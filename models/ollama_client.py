import requests
from pydantic import BaseModel

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
REQUEST_TIMEOUT_SECONDS = 300
NANOSECONDS_PER_SECOND = 1_000_000_000
CONTEXT_WINDOW_TOKENS = 4096
MAX_OUTPUT_TOKENS = 512
GENERATION_OPTIONS = {"temperature": 0, "num_predict": MAX_OUTPUT_TOKENS, "num_ctx": CONTEXT_WINDOW_TOKENS}


class OllamaRequestError(Exception):
    pass


class OllamaGenerateResponse(BaseModel):
    response: str
    eval_count: int
    total_duration: int
    load_duration: int
    # Ollama omits this field when it reuses a cached prompt.
    prompt_eval_count: int = 0


class ModelResponse(BaseModel):
    answer: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float


def build_request_body(model_name: str, prompt: str) -> dict:
    return {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": GENERATION_OPTIONS,
    }


def raise_if_request_failed(response: requests.Response) -> None:
    if not response.ok:
        raise OllamaRequestError(f"Ollama returned {response.status_code}: {response.text}")


def send_generate_request(request_body: dict) -> OllamaGenerateResponse:
    response = requests.post(
        OLLAMA_GENERATE_URL,
        json=request_body,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    raise_if_request_failed(response)
    return OllamaGenerateResponse.model_validate(response.json())


def calculate_latency_seconds(ollama_response: OllamaGenerateResponse) -> float:
    # Loading the model into memory is a one-time cost, not part of answering.
    answering_nanoseconds = ollama_response.total_duration - ollama_response.load_duration
    return round(answering_nanoseconds / NANOSECONDS_PER_SECOND, 2)


def to_model_response(ollama_response: OllamaGenerateResponse) -> ModelResponse:
    return ModelResponse(
        answer=ollama_response.response,
        input_tokens=ollama_response.prompt_eval_count,
        output_tokens=ollama_response.eval_count,
        latency_seconds=calculate_latency_seconds(ollama_response),
    )


def ask_model(model_name: str, prompt: str) -> ModelResponse:
    request_body = build_request_body(model_name, prompt)
    ollama_response = send_generate_request(request_body)
    return to_model_response(ollama_response)


if __name__ == "__main__":
    print(ask_model("gemma3:4b", "What is the capital of Turkey?"))