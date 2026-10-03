from pathlib import Path
from datasets import load_dataset

from eval.question import AnswerType, Question

TEST_SET_PATH = Path(__file__).parent / "data" / "test_set.jsonl"
SHUFFLE_SEED = 42

MMLU_DATASET_NAME = "cais/mmlu"
MMLU_SUBJECTS = [
    "elementary_mathematics",
    "high_school_geography",
    "college_physics",
    "formal_logic",
]
QUESTIONS_PER_MMLU_SUBJECT = 25
CHOICE_LETTERS = ["A", "B", "C", "D"]
MULTIPLE_CHOICE_INSTRUCTION = "Answer with the letter of the correct choice only."

GSM8K_DATASET_NAME = "openai/gsm8k"
GSM8K_QUESTION_COUNT = 100
GSM8K_ANSWER_MARKER = "####"
NUMBER_INSTRUCTION = (
    "Solve the problem step by step. "
    f"End with the final number on its own line, like: {GSM8K_ANSWER_MARKER} 42"
)


def sample_rows(dataset, row_count: int) -> list[dict]:
    shuffled_dataset = dataset.shuffle(seed=SHUFFLE_SEED)
    return list(shuffled_dataset.select(range(row_count)))


def format_choices(choices: list[str]) -> str:
    lines = [f"{letter}. {choice}" for letter, choice in zip(CHOICE_LETTERS, choices)]
    return "\n".join(lines)


def build_multiple_choice_prompt(question_text: str, choices: list[str]) -> str:
    return f"{question_text}\n{format_choices(choices)}\n\n{MULTIPLE_CHOICE_INSTRUCTION}"


def to_mmlu_question(row: dict, subject: str, position: int) -> Question:
    return Question(
        question_id=f"mmlu-{subject}-{position:03d}",
        source="mmlu",
        subject=subject,
        prompt=build_multiple_choice_prompt(row["question"], row["choices"]),
        reference_answer=CHOICE_LETTERS[row["answer"]],
        answer_type=AnswerType.MULTIPLE_CHOICE,
    )


def load_mmlu_questions(subject: str) -> list[Question]:
    dataset = load_dataset(MMLU_DATASET_NAME, subject, split="test")
    rows = sample_rows(dataset, QUESTIONS_PER_MMLU_SUBJECT)
    return [to_mmlu_question(row, subject, position) for position, row in enumerate(rows)]


def extract_gsm8k_reference_answer(solution_text: str) -> str:
    final_number = solution_text.split(GSM8K_ANSWER_MARKER)[-1]
    return final_number.strip().replace(",", "")


def to_gsm8k_question(row: dict, position: int) -> Question:
    return Question(
        question_id=f"gsm8k-{position:03d}",
        source="gsm8k",
        subject="math_word_problems",
        prompt=f"{row['question']}\n\n{NUMBER_INSTRUCTION}",
        reference_answer=extract_gsm8k_reference_answer(row["answer"]),
        answer_type=AnswerType.NUMBER,
    )


def load_gsm8k_questions() -> list[Question]:
    dataset = load_dataset(GSM8K_DATASET_NAME, "main", split="test")
    rows = sample_rows(dataset, GSM8K_QUESTION_COUNT)
    return [to_gsm8k_question(row, position) for position, row in enumerate(rows)]


def load_all_questions() -> list[Question]:
    questions = []
    for subject in MMLU_SUBJECTS:
        questions.extend(load_mmlu_questions(subject))
    questions.extend(load_gsm8k_questions())
    return questions


def write_questions(questions: list[Question], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [question.model_dump_json() for question in questions]
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    all_questions = load_all_questions()
    write_questions(all_questions, TEST_SET_PATH)
    print(f"Wrote {len(all_questions)} questions to {TEST_SET_PATH}")