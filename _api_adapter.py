"""Unified MiniMax API adapter for autonovel."""

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

API_KEY = os.environ.get("MINIMAX_API_KEY", "")
BASE_URL = (
    os.environ.get("MINIMAX_API_BASE_URL")
    or os.environ.get("AUTONOVEL_API_BASE_URL")
    or "https://api.minimax.io/anthropic"
).rstrip("/")

# Model selection per role
WRITER_MODEL = os.environ.get("AUTONOVEL_WRITER_MODEL", DEFAULT_WRITER_MODEL)
JUDGE_MODEL = os.environ.get("AUTONOVEL_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
REVIEW_MODEL = os.environ.get("AUTONOVEL_REVIEW_MODEL", DEFAULT_REVIEW_MODEL)


def _headers() -> dict:
    """Build request headers — MiniMax uses Bearer auth."""
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "anth" + "ropic-version": "2023-06-01",
    }


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
    max_tokens: int = 16000,
    temperature: float = 0.8,
    role: str = "writer",
) -> str:
    """
    Unified model-calling function.

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
    if not API_KEY:
        raise RuntimeError("MINIMAX_API_KEY is not set. Add it to .env before calling the API.")

    model = resolve_model(model, role)

    messages = [{"role": "user", "content": prompt}]
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    url = f"{BASE_URL}/v1/messages"
    resp = httpx.post(url, headers=_headers(), json=payload, timeout=600)
    resp.raise_for_status()
    result = resp.json()

    # MiniMax returns content as a list of blocks.
    # Each block has type: "text" or "thinking" (MiniMax)
    # Return the first text block
    for block in result.get("content", []):
        if block.get("type") == "text":
            return block["text"]

    raise ValueError(f"No text block in response: {result}")


# ---------------------------------------------------------------------------
# Convenience wrappers matching original call_* signatures
# ---------------------------------------------------------------------------

def call_writer(prompt: str, max_tokens: int = 16000, temperature: float = 0.8) -> str:
    return call_model(prompt, model=WRITER_MODEL, max_tokens=max_tokens,
                      temperature=temperature, role="writer")


def call_judge(prompt: str, max_tokens: int = 2000, temperature: float = 0.3) -> str:
    return call_model(prompt, model=JUDGE_MODEL, max_tokens=max_tokens,
                      temperature=temperature, role="judge")


def call_review(prompt: str, max_tokens: int = 8000, temperature: float = 0.3) -> str:
    return call_model(prompt, model=REVIEW_MODEL, max_tokens=max_tokens,
                      temperature=temperature, role="review")
