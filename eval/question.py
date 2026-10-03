from enum import StrEnum

from pydantic import BaseModel


class AnswerType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    NUMBER = "number"


class Question(BaseModel):
    question_id: str
    source: str
    subject: str
    prompt: str
    reference_answer: str
    answer_type: AnswerType