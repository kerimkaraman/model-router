import time
from dataclasses import dataclass

import requests

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
REQUEST_TIMEOUT_SECONDS = 120

@dataclass
class ModelResponse:
    answer: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float


def build_request_body(model_name: str, prompt: str) -> dict:
    return {"model": model_name, "prompt": prompt, "stream": False}


def send_generate_request(request_body: dict) -> dict:
    response = requests.post(
        OLLAMA_GENERATE_URL,
        json=request_body,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def parse_model_response(response_body: dict, latency_seconds: float) -> ModelResponse:
    return ModelResponse(
        answer=response_body["response"],
        input_tokens=response_body["prompt_eval_count"],
        output_tokens=response_body["eval_count"],
        latency_seconds=latency_seconds,
    )


def ask_model(model_name: str, prompt: str) -> ModelResponse:
    request_body = build_request_body(model_name, prompt)
    started_at = time.perf_counter()
    response_body = send_generate_request(request_body)
    latency_seconds = round(time.perf_counter() - started_at, 2)
    return parse_model_response(response_body, latency_seconds)


if __name__ == "__main__":
    message_to_send = input("Ask question: ")
    print(ask_model("gemma3:4b", message_to_send))