# Step C — CPU-only inference container (vLLM)

This folder provides a **CPU-only** vLLM container that serves an **OpenAI-compatible** API:

- `POST /v1/chat/completions` (including streaming with `data: ...` chunks and `data: [DONE]`)

CPU inference is **slow**. Use a small model for local testing.

## Build

Run from `virtualfr/backend/`:

```bash
docker build -t virtualfr-vllm-cpu -f inference/Dockerfile .
```

## Run (container exposes 8000; map to host 8001)

```bash
docker run --rm -p 8001:8000 ^
  -e MODEL=Qwen/Qwen2.5-0.5B-Instruct ^
  -e VLLM_API_KEY=token-abc123 ^
  virtualfr-vllm-cpu
```

Notes:
- First run downloads the model (can take time).
- If your CPU lacks required instruction sets for the installed CPU wheels, vLLM may fail with “Illegal instruction”.

## Point the gateway at the container

In the gateway shell (where you run `uvicorn app.main:app`):

```bash
export INTERNAL_LLM_BASE_URL=http://127.0.0.1:8001
export INTERNAL_LLM_API_KEY=token-abc123
```

Then the gateway will call:

- `POST ${INTERNAL_LLM_BASE_URL}/v1/chat/completions`

and translate the OpenAI-style stream into the app’s SSE contract (`event: token`, `event: done`).

