"""Unified MiniMax/Z.AI API adapter for autonovel."""

import os
import httpx
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_WRITER_MODEL = "auto"
DEFAULT_JUDGE_MODEL = "auto"
DEFAULT_REVIEW_MODEL = "auto"

# Provider selection: "minimax" or "glm"
PROVIDER = os.environ.get("AUTONOVEL_PROVIDER", "minimax")

# MiniMax config
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = (
    os.environ.get("MINIMAX_API_BASE_URL")
    or os.environ.get("AUTONOVEL_API_BASE_URL")
    or "https://api.minimax.io/anthropic"
).rstrip("/")

# Z.AI/GLM config
GLM_API_KEY = os.environ.get("GLM_API_KEY", "")
GLM_BASE_URL = os.environ.get("GLM_BASE_URL", "https://api.z.ai/api/coding/paas/v4").rstrip("/")

# Model selection per role
WRITER_MODEL = os.environ.get("AUTONOVEL_WRITER_MODEL", DEFAULT_WRITER_MODEL)
JUDGE_MODEL = os.environ.get("AUTONOVEL_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
REVIEW_MODEL = os.environ.get("AUTONOVEL_REVIEW_MODEL", DEFAULT_REVIEW_MODEL)


def _get_provider_config() -> tuple[str, str]:
    """Get API key and base URL for the selected provider."""
    if PROVIDER.lower() == "glm":
        return GLM_API_KEY, GLM_BASE_URL
    else:  # minimax (default)
        return MINIMAX_API_KEY, MINIMAX_BASE_URL


def _headers() -> dict:
    """Build request headers — both providers use Bearer auth."""
    api_key, _ = _get_provider_config()

    if not api_key:
        raise RuntimeError(f"API key for provider '{PROVIDER}' is not set. Add it to .env before calling the API.")

    base_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # MiniMax requires anthropic-version header
    if PROVIDER.lower() == "minimax":
        base_headers["anthropic-version"] = "2023-06-01"

    return base_headers


def resolve_model(model: str, role: str) -> str:
    """Resolve the requested model for a MiniMax request."""
    if model != "auto":
        return model
    if role == "judge":
        return JUDGE_MODEL
    if role == "review":
        return REVIEW_MODEL
    return WRITER_MODEL


def call_model(
    prompt: str,
    system: str = "",
    model: str = "auto",
    max_tokens: int = 32768,
    temperature: float = 0.8,
    role: str = "writer",
) -> str:
    """
    Unified model-calling function supporting both MiniMax and Z.AI/GLM.

    Args:
        prompt: The user message.
        system: System prompt.
        model: Model name. Use "auto" to pick based on role.
        max_tokens: Max tokens to generate.
        temperature: Sampling temperature.
        role: "writer" | "judge" | "review" — selects default model if model="auto".

    Returns:
        The generated text from the model.
    """
    model = resolve_model(model, role)
    _, base_url = _get_provider_config()

    messages = [{"role": "user", "content": prompt}]
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    url = f"{base_url}/chat/completions"
    resp = httpx.post(url, headers=_headers(), json=payload, timeout=600)
    resp.raise_for_status()
    result = resp.json()

    # Handle response format differences between providers
    if PROVIDER.lower() == "glm":
        # Z.AI/GLM returns OpenAI-style format
        # Some GLM models use "reasoning_content" instead of "content"
        choice = result.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        
        # If content is empty, check for reasoning_content
        if not content:
            content = choice.get("message", {}).get("reasoning_content", "")
        
        return content
    else:
        # MiniMax returns content as a list of blocks with type "text" or "thinking"
        for block in result.get("content", []):
            if block.get("type") == "text":
                return block["text"]

    raise ValueError(f"No text block in response: {result}")


# ---------------------------------------------------------------------------
# Convenience wrappers matching original call_* signatures
# ---------------------------------------------------------------------------

def call_writer(prompt: str, max_tokens: int = 32768, temperature: float = 0.8) -> str:
    return call_model(prompt, model=WRITER_MODEL, max_tokens=max_tokens,
                      temperature=temperature, role="writer")


def call_judge(prompt: str, max_tokens: int = 2000, temperature: float = 0.3) -> str:
    return call_model(prompt, model=JUDGE_MODEL, max_tokens=max_tokens,
                      temperature=temperature, role="judge")


def call_review(prompt: str, max_tokens: int = 8000, temperature: float = 0.3) -> str:
    return call_model(prompt, model=REVIEW_MODEL, max_tokens=max_tokens,
                      temperature=temperature, role="review")
