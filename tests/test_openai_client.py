from types import SimpleNamespace
from unittest.mock import Mock
import argparse
import pytest
from models import openai_client
from eval import run_model
from eval.question import AnswerType, Question


def test_request_and_usage(monkeypatch):
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(
        output_text="B", id="resp_test", model="gpt-6-luna", status="completed",
        incomplete_details=None,
        usage=SimpleNamespace(input_tokens=20, output_tokens=12,
            input_tokens_details=SimpleNamespace(cached_tokens=5),
            output_tokens_details=SimpleNamespace(reasoning_tokens=8)))
    monkeypatch.setattr(openai_client, "get_client", lambda: client)
    result = openai_client.ask_model("gpt-6-luna", "Question")
    args = client.responses.create.call_args.kwargs
    assert args["model"] == "gpt-6-luna"
    assert args["reasoning"] == {"effort": "low"}
    assert args["store"] is False
    assert "temperature" not in args
    assert (result.input_tokens, result.output_tokens) == (20, 12)
    assert (result.cached_input_tokens, result.reasoning_tokens) == (5, 8)


def test_missing_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(openai_client, "ENV_PATH", tmp_path / ".env")
    openai_client.get_client.cache_clear()
    with pytest.raises(ValueError, match="Set OPENAI_API_KEY"):
        openai_client.get_client()
    openai_client.get_client.cache_clear()


def test_incomplete_not_correct(monkeypatch):
    response = openai_client.ModelResponse(answer="B", input_tokens=20, output_tokens=12,
        latency_seconds=1, response_id="resp_test", resolved_model="gpt-6-luna",
        status="incomplete", incomplete_reason="max_output_tokens")
    monkeypatch.setattr(run_model, "ask_model", lambda *args: response)
    q = Question(question_id="q1", source="test", subject="test", prompt="Question",
        reference_answer="B", answer_type=AnswerType.MULTIPLE_CHOICE)
    assert not run_model.answer_question("gpt-6-luna", q).is_correct


def test_existing_results_preserved(monkeypatch, tmp_path):
    monkeypatch.setattr(run_model, "RESULTS_DIR", tmp_path)
    (tmp_path / "dev").mkdir()
    path = tmp_path / "dev" / "gpt-6-luna.jsonl"
    path.write_text("old result")
    with pytest.raises(FileExistsError):
        run_model.run_model("gpt-6-luna", [])
    assert path.read_text() == "old result"


@pytest.mark.parametrize("value", ["0", "-1"])
def test_positive_sampling(value):
    with pytest.raises(argparse.ArgumentTypeError):
        run_model.positive_int(value)
