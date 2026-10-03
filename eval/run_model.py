import argparse
from pathlib import Path

from pydantic import BaseModel

from eval.question import Question
from eval.scoring import is_correct
from models.ollama_client import ask_model

TEST_SET_PATH = Path(__file__).parent / "data" / "test_set.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"


class QuestionResult(BaseModel):
    question_id: str
    model_name: str
    model_answer: str
    is_correct: bool
    input_tokens: int
    output_tokens: int
    latency_seconds: float


def load_questions(test_set_path: Path) -> list[Question]:
    lines = test_set_path.read_text().splitlines()
    return [Question.model_validate_json(line) for line in lines]


def build_results_path(model_name: str) -> Path:
    file_name = model_name.replace(":", "_") + ".jsonl"
    return RESULTS_DIR / file_name


def answer_question(model_name: str, question: Question) -> QuestionResult:
    model_response = ask_model(model_name, question.prompt)
    return QuestionResult(
        question_id=question.question_id,
        model_name=model_name,
        model_answer=model_response.answer,
        is_correct=is_correct(question, model_response.answer),
        input_tokens=model_response.input_tokens,
        output_tokens=model_response.output_tokens,
        latency_seconds=model_response.latency_seconds,
    )


def append_result(result: QuestionResult, results_path: Path) -> None:
    with results_path.open("a") as results_file:
        results_file.write(result.model_dump_json() + "\n")


def print_progress(position: int, question_count: int, result: QuestionResult) -> None:
    verdict = "correct" if result.is_correct else "wrong"
    print(
        f"[{position}/{question_count}] {result.question_id}: "
        f"{verdict} in {result.latency_seconds}s"
    )


def run_model(model_name: str, questions: list[Question]) -> None:
    results_path = build_results_path(model_name)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.unlink(missing_ok=True)
    for position, question in enumerate(questions, start=1):
        result = answer_question(model_name, question)
        append_result(result, results_path)
        print_progress(position, len(questions), result)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask every test question to one model.")
    parser.add_argument("model_name")
    parser.add_argument("--step", type=int, default=1, help="use every Nth question")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    selected_questions = load_questions(TEST_SET_PATH)[:: arguments.step]
    run_model(arguments.model_name, selected_questions)