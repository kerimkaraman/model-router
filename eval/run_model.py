import argparse
from pathlib import Path

from pydantic import BaseModel

from eval.question import Question
from eval.scoring import SCORER_VERSION, score_answer
from models.openai_client import MODEL_NAMES, MAX_OUTPUT_TOKENS, REASONING_EFFORT, ask_model, get_client

DATA_DIR = Path(__file__).parent / "data"
TEST_SET_PATH = DATA_DIR / "dev.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"


class QuestionResult(BaseModel):
    question_id: str
    model_name: str
    model_answer: str
    is_correct: bool
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    response_id: str | None = None
    resolved_model: str | None = None
    response_status: str = "completed"
    incomplete_reason: str | None = None
    reasoning_effort: str | None = None
    max_output_tokens: int | None = None
    score_status: str = "legacy"
    scorer_version: str = "legacy"
    extracted_answer: str | None = None
    dataset_split: str = "legacy"
    dataset_sha256: str | None = None


def load_questions(test_set_path: Path) -> list[Question]:
    lines = test_set_path.read_text().splitlines()
    return [Question.model_validate_json(line) for line in lines]


def build_results_path(model_name: str, split: str = "dev") -> Path:
    file_name = model_name.replace(":", "_") + ".jsonl"
    return (RESULTS_DIR if split == "legacy" else RESULTS_DIR / split) / file_name


def answer_question(model_name: str, question: Question) -> QuestionResult:
    model_response = ask_model(model_name, question.prompt)
    score = score_answer(question, model_response.answer)
    return QuestionResult(
        question_id=question.question_id,
        model_name=model_name,
        model_answer=model_response.answer,
        is_correct=(model_response.status == "completed" and score.status == "correct"),
        score_status=score.status if model_response.status == "completed" else "incomplete",
        scorer_version=SCORER_VERSION,
        extracted_answer=score.extracted_answer,
        input_tokens=model_response.input_tokens,
        output_tokens=model_response.output_tokens,
        latency_seconds=model_response.latency_seconds,
        cached_input_tokens=model_response.cached_input_tokens,
        reasoning_tokens=model_response.reasoning_tokens,
        response_id=model_response.response_id,
        resolved_model=model_response.resolved_model,
        response_status=model_response.status,
        incomplete_reason=model_response.incomplete_reason,
        reasoning_effort=REASONING_EFFORT,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )


def append_result(result: QuestionResult, results_path: Path) -> None:
    with results_path.open("a") as results_file:
        results_file.write(result.model_dump_json() + "\n")


def print_progress(position: int, question_count: int, result: QuestionResult) -> None:
    verdict = result.score_status
    print(
        f"[{position}/{question_count}] {result.question_id}: "
        f"{verdict} in {result.latency_seconds}s"
    )


def run_model(model_name: str, questions: list[Question], overwrite: bool = False,
              split: str = "dev", dataset_sha256: str | None = None) -> None:
    results_path = build_results_path(model_name, split)
    if results_path.exists() and not overwrite:
        raise FileExistsError(f"Results already exist: {results_path}. Use --overwrite to replace them.")
    get_client()
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w" if overwrite else "x"):
        pass
    for position, question in enumerate(questions, start=1):
        result = answer_question(model_name, question)
        result.dataset_split = split
        result.dataset_sha256 = dataset_sha256
        append_result(result, results_path)
        print_progress(position, len(questions), result)


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate OpenAI Luna, Sol and Astra.")
    parser.add_argument("model_name", nargs="?", choices=MODEL_NAMES)
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--all", action="store_true", help="evaluate all three models")
    parser.add_argument("--step", type=positive_int, default=1, help="use every Nth question")
    parser.add_argument("--limit", type=positive_int, help="maximum questions per model")
    parser.add_argument("--overwrite", action="store_true", help="replace existing results")
    args = parser.parse_args()
    if bool(args.model_name) == args.all:
        parser.error("choose a model_name OR --all")
    return args


if __name__ == "__main__":
    arguments = parse_arguments()
    import hashlib
    dataset_path = DATA_DIR / f"{arguments.split}.jsonl"
    dataset_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    selected_questions = load_questions(dataset_path)[:: arguments.step]
    if arguments.limit is not None:
        selected_questions = selected_questions[:arguments.limit]
    models = MODEL_NAMES if arguments.all else (arguments.model_name,)
    if not arguments.overwrite:
        for model in models:
            if build_results_path(model, arguments.split).exists():
                raise SystemExit(f"Results for {model} already exist. Use --overwrite explicitly.")
    print(f"Paid API evaluation: {len(selected_questions)} questions x {len(models)} models.")
    for model in models:
        run_model(model, selected_questions, overwrite=arguments.overwrite,
                  split=arguments.split, dataset_sha256=dataset_hash)
