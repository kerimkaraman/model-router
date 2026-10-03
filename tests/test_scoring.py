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
        ("Allen is 99 now, so he will be 109.", 109),
        ("I cannot solve this.", None),
    ],
)
def test_extract_final_number(model_answer, expected_number):
    assert extract_final_number(model_answer) == expected_number