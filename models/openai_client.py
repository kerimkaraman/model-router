import os
from functools import lru_cache
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
MODEL_NAMES = ("gpt-6-luna", "gpt-6-sol", "gpt-6-astra")
REASONING_EFFORT = "low"
MAX_OUTPUT_TOKENS = 4096


class ModelResponse(BaseModel):
    answer: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    latency_seconds: float
    response_id: str
    resolved_model: str
    status: str
    incomplete_reason: str | None = None


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    load_dotenv(ENV_PATH, override=False)
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise ValueError(f"Set OPENAI_API_KEY in {ENV_PATH} before running evaluations.")
    return OpenAI(timeout=120.0, max_retries=0)


def ask_model(model_name: str, prompt: str) -> ModelResponse:
    if model_name not in MODEL_NAMES:
        raise ValueError(f"Choose one of: {', '.join(MODEL_NAMES)}")
    client = get_client()
    started = perf_counter()
    response = client.responses.create(
        model=model_name, input=prompt,
        reasoning={"effort": REASONING_EFFORT},
        max_output_tokens=MAX_OUTPUT_TOKENS,
        service_tier="default", store=False,
    )
    elapsed = perf_counter() - started
    if response.usage is None:
        raise RuntimeError("OpenAI returned no usage information.")
    return ModelResponse(
        answer=response.output_text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cached_input_tokens=getattr(response.usage.input_tokens_details, "cached_tokens", 0),
        reasoning_tokens=getattr(response.usage.output_tokens_details, "reasoning_tokens", 0),
        latency_seconds=round(elapsed, 4),
        response_id=response.id, resolved_model=response.model, status=response.status,
        incomplete_reason=response.incomplete_details.reason if response.incomplete_details else None,
    )
