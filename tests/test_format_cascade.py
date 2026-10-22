from decimal import Decimal
import pytest
from eval.format_cascade import accept_format, format_simulation
from eval.oracle_cascade import MODELS, Rate
from eval.question import AnswerType
from eval.run_model import QuestionResult


def row(model, answer, correct, status="completed"):
    return QuestionResult(question_id="q", model_name=model, model_answer=answer,
        is_correct=correct, input_tokens=10, output_tokens=5, latency_seconds=1,
        response_status=status, score_status="correct" if correct else ("incomplete" if status != "completed" else "incorrect"),
        scorer_version="strict-v2", dataset_split="dev", dataset_sha256="fixture",
        reasoning_effort="low", max_output_tokens=4096)


def rates():
    return {m: Rate(Decimal(1), Decimal(0), Decimal(1)) for m in MODELS}


def test_well_formed_wrong_answer_stops_without_gold():
    runs = {m: [row(m, "B", i > 0)] for i, m in enumerate(MODELS)}
    summaries, traces = format_simulation(runs, rates(), {"q": AnswerType.MULTIPLE_CHOICE})
    assert traces[0]["attempted_models"] == [MODELS[0]]
    assert traces[0]["accepted"]
    assert summaries[-1]["correct_count"] == 0


def test_changing_gold_labels_does_not_change_route():
    runs = {m: [row(m, "B", True)] for m in MODELS}
    _, before = format_simulation(runs, rates(), {"q": AnswerType.MULTIPLE_CHOICE})
    for rows in runs.values():
        rows[0].is_correct = False
        rows[0].score_status = "incorrect"
    _, after = format_simulation(runs, rates(), {"q": AnswerType.MULTIPLE_CHOICE})
    assert before[0]["attempted_models"] == after[0]["attempted_models"]
    assert before[0]["estimated_cost_usd"] == after[0]["estimated_cost_usd"]


def test_unparseable_and_incomplete_escalate_and_pay_all_calls():
    runs = {MODELS[0]: [row(MODELS[0], "B or C", False)],
            MODELS[1]: [row(MODELS[1], "B", False, "incomplete")],
            MODELS[2]: [row(MODELS[2], "B", True)]}
    summaries, traces = format_simulation(runs, rates(), {"q": AnswerType.MULTIPLE_CHOICE})
    assert traces[0]["attempted_models"] == list(MODELS)
    assert traces[0]["accepted"] and traces[0]["is_correct"]
    assert summaries[-1]["calls"] == 3
    assert Decimal(summaries[-1]["estimated_cost_usd"]) == Decimal("0.000045")
    assert summaries[-1]["average_latency_seconds"] == 3


def test_all_unparseable_stops_exhausted():
    runs = {m: [row(m, "I do not know", False)] for m in MODELS}
    _, traces = format_simulation(runs, rates(), {"q": AnswerType.MULTIPLE_CHOICE})
    assert len(traces[0]["attempted_models"]) == 3
    assert not traces[0]["accepted"]


@pytest.mark.parametrize("answer,expected", [("#### 42", True), ("#### 42 cats", False), ("42", True), ("Maybe 42", False)])
def test_numeric_format_only(answer, expected):
    assert accept_format(AnswerType.NUMBER, answer, "completed") == expected
