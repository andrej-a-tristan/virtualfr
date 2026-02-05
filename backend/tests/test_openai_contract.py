import os

import httpx
import pytest


def _base_url() -> str:
    return os.getenv("INTERNAL_LLM_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def _api_key() -> str:
    return os.getenv("INTERNAL_LLM_API_KEY", "").strip()


def _endpoint() -> str:
    return f"{_base_url()}/v1/chat/completions"


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _skip_if_unreachable(exc: Exception):
    pytest.skip(
        f"Internal LLM not reachable at {_base_url()} "
        f"(set INTERNAL_LLM_BASE_URL). Start mock_main or the vLLM container. Error: {exc}"
    )


def test_chat_completions_non_stream():
    payload = {
        "model": os.getenv("MODEL", "Qwen/Qwen2.5-0.5B-Instruct"),
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.post(_endpoint(), headers=_headers(), json=payload)
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        _skip_if_unreachable(e)

    assert r.status_code == 200
    data = r.json()
    assert "choices" in data and isinstance(data["choices"], list) and data["choices"]

    # OpenAI-style: choices[0].message.content
    msg = data["choices"][0].get("message") or {}
    content = msg.get("content")
    assert isinstance(content, str)
    assert content.strip() != ""


def test_chat_completions_stream():
    payload = {
        "model": os.getenv("MODEL", "Qwen/Qwen2.5-0.5B-Instruct"),
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }

    saw_data_line = False
    saw_done = False

    try:
        with httpx.Client(timeout=30.0) as client:
            with client.stream("POST", _endpoint(), headers=_headers(), json=payload) as r:
                assert r.status_code == 200
                for line in r.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        saw_data_line = True
                        if line.strip() == "data: [DONE]":
                            saw_done = True
                            break
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        _skip_if_unreachable(e)

    assert saw_data_line, "Expected at least one OpenAI SSE line starting with 'data: '"
    assert saw_done, "Expected the stream to end with 'data: [DONE]'"

