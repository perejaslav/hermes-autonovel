"""Unified LLM API adapter for autonovel."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

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

# Provider selection: "agent", "glm", or "openai_compatible"
PROVIDER = os.environ.get("AUTONOVEL_PROVIDER", "agent")

# Generic OpenAI-compatible model API config
MODEL_API_KEY = os.environ.get("MODEL_API_KEY", "")
MODEL_API_BASE_URL = os.environ.get("MODEL_API_BASE_URL", "").rstrip("/")
MODEL_API_HEADERS = os.environ.get("MODEL_API_HEADERS", "")

# Z.AI/GLM config
GLM_API_KEY = os.environ.get("GLM_API_KEY", "")
GLM_BASE_URL = os.environ.get("GLM_BASE_URL", "https://api.z.ai/api/coding/paas/v4").rstrip("/")

# Hermes Agent request/response config
AGENT_REQUEST_DIR = os.environ.get("AUTONOVEL_AGENT_REQUEST_DIR", ".autonovel/agent_requests")
AGENT_RESPONSE_FILE = os.environ.get("AUTONOVEL_AGENT_RESPONSE_FILE", "")

# Model selection per role
WRITER_MODEL = os.environ.get("AUTONOVEL_WRITER_MODEL", DEFAULT_WRITER_MODEL)
JUDGE_MODEL = os.environ.get("AUTONOVEL_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
REVIEW_MODEL = os.environ.get("AUTONOVEL_REVIEW_MODEL", DEFAULT_REVIEW_MODEL)


def _get_provider_config() -> tuple[str, str]:
    """Get API key and base URL for the selected provider."""
    provider = PROVIDER.lower()
    if provider == "agent":
        return "", ""
    if provider == "glm":
        return GLM_API_KEY, GLM_BASE_URL
    if provider == "openai_compatible":
        return MODEL_API_KEY, MODEL_API_BASE_URL
    raise RuntimeError(f"Unknown provider '{PROVIDER}'. Use agent, glm, or openai_compatible.")


def _headers() -> dict:
    """Build request headers — both providers use Bearer auth."""
    api_key, _ = _get_provider_config()

    if PROVIDER.lower() == "agent":
        return {"Content-Type": "application/json"}

    if not api_key:
        raise RuntimeError(f"API key for provider '{PROVIDER}' is not set. Add it to .env before calling the API.")

    base_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if MODEL_API_HEADERS:
        try:
            extra_headers = json.loads(MODEL_API_HEADERS)
        except json.JSONDecodeError as exc:
            raise RuntimeError("MODEL_API_HEADERS must be valid JSON object text.") from exc
        if not isinstance(extra_headers, dict):
            raise RuntimeError("MODEL_API_HEADERS must decode to a JSON object.")
        base_headers.update({str(k): str(v) for k, v in extra_headers.items()})

    return base_headers


def resolve_model(model: str, role: str) -> str:
    """Resolve the requested model for a model request."""
    if model != "auto":
        return model
    if role == "judge":
        return JUDGE_MODEL
    if role == "review":
        return REVIEW_MODEL
    return WRITER_MODEL


def _read_agent_response(path: Path) -> str:
    """Read a Hermes Agent response file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, str):
        return data
    content = data.get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"Hermes Agent response file has no text content: {path}")
    return content


def _call_agent(
    prompt: str,
    system: str,
    model: str,
    max_tokens: int,
    temperature: float,
    role: str,
) -> str:
    """Create a request for Hermes Agent or read a supplied response file."""
    if AGENT_RESPONSE_FILE:
        return _read_agent_response(Path(AGENT_RESPONSE_FILE))

    request_dir = Path(AGENT_REQUEST_DIR)
    request_dir.mkdir(parents=True, exist_ok=True)
    request_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    response_path = request_dir / f"{request_id}.response.json"
    request_path = request_dir / f"{request_id}.request.json"
    payload = {
        "id": request_id,
        "provider": "agent",
        "role": role,
        "model": model,
        "system": system,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "response_path": str(response_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    request_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    raise RuntimeError(
        "Hermes Agent response required. "
        f"Review request file {request_path} with the current Hermes model, "
        f"write JSON {{\"content\": \"...\"}} to {response_path}, then rerun with "
        f"AUTONOVEL_AGENT_RESPONSE_FILE={response_path}."
    )


def call_model(
    prompt: str,
    system: str = "",
    model: str = "auto",
    max_tokens: int = 32768,
    temperature: float = 0.8,
    role: str = "writer",
) -> str:
    """
    Unified model-calling function supporting Hermes Agent request files,
    Z.AI/GLM, and OpenAI-compatible APIs.

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
    if PROVIDER.lower() == "agent":
        return _call_agent(prompt, system, model, max_tokens, temperature, role)

    _, base_url = _get_provider_config()
    if not base_url:
        raise RuntimeError(f"Base URL for provider '{PROVIDER}' is not set.")

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
    if PROVIDER.lower() in {"glm", "openai_compatible"}:
        # Z.AI/GLM and OpenAI-compatible providers return OpenAI-style format
        # Some GLM models use "reasoning_content" instead of "content"
        choice = result.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        
        # If content is empty, check for reasoning_content
        if not content:
            content = choice.get("message", {}).get("reasoning_content", "")
        
        return content
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
