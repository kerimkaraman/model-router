import argparse
from itertools import combinations
from pathlib import Path
from pydantic import BaseModel
from eval.run_model import QuestionResult, build_results_path

from models.openai_client import MODEL_NAMES


class ModelSummary(BaseModel):
    model_name: str
    question_count: int
    correct_count: int
    accuracy_percent: float
    average_latency_seconds: float
    total_input_tokens: int
    unparseable_count: int = 0
    incomplete_count: int = 0
    total_output_tokens: int


class AgreementSummary(BaseModel):
    both_correct_count: int
    only_strong_correct_count: int
    only_small_correct_count: int
    both_wrong_count: int


def load_results(results_path: Path) -> list[QuestionResult]:
    lines = results_path.read_text().splitlines()
    if not lines:
        raise ValueError(f"No results in {results_path}")
    return [QuestionResult.model_validate_json(line) for line in lines]


def count_correct(results: list[QuestionResult]) -> int:
    return sum(result.is_correct for result in results)


def calculate_percent(part_count: int, total_count: int) -> float:
    return round(100 * part_count / total_count, 1)


def calculate_average_latency_seconds(results: list[QuestionResult]) -> float:
    total_latency_seconds = sum(result.latency_seconds for result in results)
    return round(total_latency_seconds / len(results), 2)


def summarize_model(model_name: str, results: list[QuestionResult]) -> ModelSummary:
    correct_count = count_correct(results)
    return ModelSummary(
        unparseable_count=sum(r.score_status == "unparseable" for r in results),
        incomplete_count=sum(r.response_status != "completed" for r in results),
        model_name=model_name,
        question_count=len(results),
        correct_count=correct_count,
        accuracy_percent=calculate_percent(correct_count, len(results)),
        average_latency_seconds=calculate_average_latency_seconds(results),
        total_input_tokens=sum(result.input_tokens for result in results),
        total_output_tokens=sum(result.output_tokens for result in results),
    )


def find_correct_question_ids(results: list[QuestionResult]) -> set[str]:
    return {result.question_id for result in results if result.is_correct}


def summarize_agreement(
    small_results: list[QuestionResult], strong_results: list[QuestionResult]
) -> AgreementSummary:
    first_metadata = {(r.scorer_version, r.dataset_split, r.dataset_sha256) for r in small_results}
    second_metadata = {(r.scorer_version, r.dataset_split, r.dataset_sha256) for r in strong_results}
    if len(first_metadata) != 1 or first_metadata != second_metadata:
        raise ValueError("Comparison requires matching dataset and scorer versions")
    first_ids = [r.question_id for r in small_results]
    second_ids = [r.question_id for r in strong_results]
    if (len(set(first_ids)) != len(first_ids) or len(set(second_ids)) != len(second_ids)
            or set(first_ids) != set(second_ids)):
        raise ValueError("Comparison requires identical, unique question IDs.")
    small_correct_ids = find_correct_question_ids(small_results)
    strong_correct_ids = find_correct_question_ids(strong_results)
    either_correct_count = len(small_correct_ids | strong_correct_ids)
    return AgreementSummary(
        both_correct_count=len(small_correct_ids & strong_correct_ids),
        only_strong_correct_count=len(strong_correct_ids - small_correct_ids),
        only_small_correct_count=len(small_correct_ids - strong_correct_ids),
        both_wrong_count=len(small_results) - either_correct_count,
    )


def print_model_summary(summary: ModelSummary) -> None:
    print(
        f"{summary.model_name}: "
        f"{summary.correct_count}/{summary.question_count} correct "
        f"({summary.accuracy_percent}%), "
        f"{summary.average_latency_seconds}s per question, "
        f"{summary.total_input_tokens} input tokens, "
        f"{summary.total_output_tokens} output tokens, "
        f"{summary.unparseable_count} unparseable, {summary.incomplete_count} incomplete"
    )


def print_agreement_summary(summary: AgreementSummary) -> None:
    print(f"both correct: {summary.both_correct_count}")
    print(f"only strong correct: {summary.only_strong_correct_count}")
    print(f"only small correct: {summary.only_small_correct_count}")
    print(f"both wrong: {summary.both_wrong_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize results without API calls.")
    parser.add_argument("--split", choices=("dev", "test", "legacy"), default="dev")
    parser.add_argument("models", nargs="*", default=list(MODEL_NAMES))
    results = {}
    args = parser.parse_args()
    for model in args.models:
        path = build_results_path(model, args.split)
        if not path.exists():
            print(f"{model}: no results yet")
            continue
        results[model] = load_results(path)
        print_model_summary(summarize_model(model, results[model]))
    for first, second in combinations(results, 2):
        print(f"\n{first} (small) vs {second} (strong):")
        print_agreement_summary(summarize_agreement(results[first], results[second]))
