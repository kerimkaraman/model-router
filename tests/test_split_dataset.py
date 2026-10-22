import pytest
from eval.question import Question, AnswerType
from eval.split_dataset import split_questions


def questions():
    return [Question(question_id=f"{subject}-{i}", source="fixture", subject=subject,
        prompt=f"{subject} question {i}", reference_answer="A", answer_type=AnswerType.MULTIPLE_CHOICE)
        for subject in ("math", "logic") for i in range(10)]


def test_frozen_stratified_split():
    source = questions()
    dev, test = split_questions(source, {"math-0"})
    assert (dev, test) == split_questions(source, {"math-0"})
    dev_ids = {q.question_id for q in dev}
    test_ids = {q.question_id for q in test}
    assert not dev_ids & test_ids
    assert dev_ids | test_ids == {q.question_id for q in source}
    assert "math-0" in dev_ids
    assert len(dev) == 12 and len(test) == 8
    assert sum(q.subject == "math" for q in dev) == 6


def test_duplicate_input_rejected():
    source = questions()
    with pytest.raises(ValueError, match="Duplicate"):
        split_questions(source + [source[0]])
