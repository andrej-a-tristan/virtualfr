FROM python:3.12-slim

# CPU-only vLLM container (slow on CPU; intended for local dev/testing).
# Docs: https://docs.vllm.ai/en/stable/getting_started/installation/cpu/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps requested:
# - git, curl: for basic tooling / debugging
# - libtcmalloc-minimal4: recommended by vLLM CPU docs (LD_PRELOAD)
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl libtcmalloc-minimal4 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install vLLM CPU build.
# vLLM CPU wheels require Torch CPU; use the PyTorch CPU extra index.
# The `vllm-cpu` package exists on PyPI and is the simplest path for CPU-only installs.
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu vllm-cpu

# Default model (small-ish; still slow on CPU).
ENV MODEL="Qwen/Qwen2.5-0.5B-Instruct"

# vLLM OpenAI-compatible server listens on 8000 in-container.
EXPOSE 8000

# Recommended for vLLM CPU: preload tcmalloc.
ENV LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtcmalloc_minimal.so.4"

# Run the OpenAI-compatible server (serves POST /v1/chat/completions).
# Note: vLLM expects --api-key even if empty; we pass env var.
CMD ["bash", "-lc", "vllm serve \"$MODEL\" --host 0.0.0.0 --port 8000 --dtype auto --api-key \"${VLLM_API_KEY:-}\""]

