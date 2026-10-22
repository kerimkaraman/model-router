import pytest

from eval.scoring import extract_choice_letter, extract_final_number


@pytest.mark.parametrize(
    ("model_answer", "expected_letter"),
    [
        ("C", "C"),
        ("C.", "C"),
        ("**C**", "C"),
        ("The answer is C", "C"),
        ("C. 22", "C"),
        ("I am not sure", None),
    ],
)
def test_extract_choice_letter(model_answer, expected_letter):
    assert extract_choice_letter(model_answer) == expected_letter


@pytest.mark.parametrize(
    ("model_answer", "expected_number"),
    [
        ("7x + 11x = 162, so x = 9.\n#### 109", 109),
        ("#### 109\nSo Allen will be 109 in 10 years.", 109),
        ("#### $1,250.50", 1250.5),
        ("#### -4", -4),
        ("Allen is 99 now, so he will be 109.", None),
        ("I cannot solve this.", None),
    ],
)
def test_extract_final_number(model_answer, expected_number):
    assert extract_final_number(model_answer) == expected_number

@pytest.mark.parametrize("text", ["A is incorrect. The answer is C.", "The answer is B or C.", "A\nB", "Maybe B", "C or D"])
def test_reject_ambiguous_choices(text):
    assert extract_choice_letter(text) is None


@pytest.mark.parametrize(("text", "expected"), [("#### 1/2", 0.5), ("#### 1e3", 1000), ("42", 42), ("#### 1/0", None), ("#### 1 or 2", None), ("#### 1\n#### 2", None), ("I cannot solve it; the question mentions 42.", None)])
def test_strict_numbers(text, expected):
    assert extract_final_number(text) == expected


def test_unparseable_is_distinct_from_wrong():
    from eval.question import Question, AnswerType
    from eval.scoring import score_answer
    q = Question(question_id="q", source="test", subject="test", prompt="Choose", reference_answer="B", answer_type=AnswerType.MULTIPLE_CHOICE)
    assert score_answer(q, "B").status == "correct"
    assert score_answer(q, "C").status == "incorrect"
    assert score_answer(q, "B or C").status == "unparseable"
