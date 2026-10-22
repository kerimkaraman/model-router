import re
from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import BaseModel
from eval.question import AnswerType, Question

SCORER_VERSION = "strict-v2"
FINAL_ANSWER_MARKER = "####"
NUMBER = r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?"
NUMBER_PATTERN = re.compile(rf"({NUMBER})(?:\s*/\s*({NUMBER}))?")


class Score(BaseModel):
    status: Literal["correct", "incorrect", "unparseable"]
    extracted_answer: str | None = None


def strip_formatting(text: str) -> str:
    return text.strip().replace("**", "").replace("`", "").strip()


def extract_choice_letter(model_answer: str) -> str | None:
    text = strip_formatting(model_answer)
    # The prompt requests one choice only. Explanations with multiple options are ambiguous.
    match = re.fullmatch(
        r"(?:(?:the\s+)?(?:final\s+)?answer\s*(?:is\s*|:\s*))?"
        r"([ABCD])(?:[.)])?(?:\s+[-+]?\d+(?:\.\d+)?[.]?)?",
        text, flags=re.IGNORECASE,
    )
    return match.group(1).upper() if match else None


def parse_number(number_text: str) -> Decimal:
    text = strip_formatting(number_text).removeprefix("$").strip()
    if text.endswith("."):
        text = text[:-1]
    match = NUMBER_PATTERN.fullmatch(text)
    if not match:
        raise ValueError("Expected one complete numeric answer")
    numerator = Decimal(match.group(1).replace(",", ""))
    if match.group(2):
        denominator = Decimal(match.group(2).replace(",", ""))
        if denominator == 0:
            raise ValueError("Zero denominator")
        return numerator / denominator
    return numerator


def extract_final_number(model_answer: str) -> Decimal | None:
    text = model_answer.strip()
    if FINAL_ANSWER_MARKER in text:
        # Multiple final-answer markers are not accepted as an unambiguous answer.
        if text.count(FINAL_ANSWER_MARKER) != 1:
            return None
        tail = text.split(FINAL_ANSWER_MARKER, 1)[1].strip()
        text = tail.splitlines()[0] if tail else ""
    # Without a marker, only an entirely numeric response is accepted.
    try:
        return parse_number(text)
    except (ValueError, InvalidOperation):
        return None


def score_answer(question: Question, model_answer: str) -> Score:
    if question.answer_type == AnswerType.MULTIPLE_CHOICE:
        answer = extract_choice_letter(model_answer)
        expected = question.reference_answer.strip().upper()
        correct = answer == expected
    else:
        answer = extract_final_number(model_answer)
        correct = answer == parse_number(question.reference_answer)
    if answer is None:
        return Score(status="unparseable")
    return Score(status="correct" if correct else "incorrect", extracted_answer=str(answer))


def is_choice_correct(model_answer: str, reference_answer: str) -> bool:
    return extract_choice_letter(model_answer) == reference_answer.strip().upper()


def is_number_correct(model_answer: str, reference_answer: str) -> bool:
    return extract_final_number(model_answer) == parse_number(reference_answer)


def is_correct(question: Question, model_answer: str) -> bool:
    return score_answer(question, model_answer).status == "correct"
