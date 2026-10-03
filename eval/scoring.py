import re

from eval.question import AnswerType, Question

FINAL_ANSWER_MARKER = "####"
CHOICE_LETTER_PATTERN = re.compile(r"\b([ABCD])\b")
NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")


def extract_choice_letter(model_answer: str) -> str | None:
    match = CHOICE_LETTER_PATTERN.search(model_answer)
    return match.group(1) if match else None


def parse_number(number_text: str) -> float:
    return float(number_text.replace(",", "").rstrip("."))


def find_numbers(text: str) -> list[float]:
    return [parse_number(number_text) for number_text in NUMBER_PATTERN.findall(text)]


def extract_final_number(model_answer: str) -> float | None:
    if FINAL_ANSWER_MARKER in model_answer:
        numbers_after_marker = find_numbers(model_answer.split(FINAL_ANSWER_MARKER)[-1])
        return numbers_after_marker[0] if numbers_after_marker else None
    # Models sometimes skip the marker; the last number is then the best guess.
    all_numbers = find_numbers(model_answer)
    return all_numbers[-1] if all_numbers else None


def is_choice_correct(model_answer: str, reference_answer: str) -> bool:
    return extract_choice_letter(model_answer) == reference_answer


def is_number_correct(model_answer: str, reference_answer: str) -> bool:
    return extract_final_number(model_answer) == float(reference_answer)


def is_correct(question: Question, model_answer: str) -> bool:
    if question.answer_type == AnswerType.MULTIPLE_CHOICE:
        return is_choice_correct(model_answer, question.reference_answer)
    return is_number_correct(model_answer, question.reference_answer)