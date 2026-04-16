"""Ollama LLM service — local, free inference via Ollama (LLaMA3 / DeepSeek).

Requires Ollama running locally:  https://ollama.com
Pull a model first:
    ollama pull llama3
    ollama pull deepseek-r1:8b
"""

import httpx
import logging
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# Timeout for generation — local models can be slow on CPU
_TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)


# ------------------------------------------------------------------
# Core public function
# ------------------------------------------------------------------
def generate_response(
    context: str,
    query: str,
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Send *context + query* to a locally-running Ollama model and return
    the generated text.

    This is the single entry-point the solver pipeline should call.

    Args:
        context: Retrieved RAG context (already formatted).
        query: The user's math question.
        system_prompt: Optional system instruction (persona, rules, etc.).
        temperature: Sampling temperature (lower = more deterministic).
        max_tokens: Maximum tokens in the response.

    Returns:
        The model's response text.

    Raises:
        ``OllamaConnectionError`` if the Ollama server is unreachable.
        ``OllamaGenerationError`` on any other generation failure.
    """
    # Build the user message that merges RAG context + query
    user_message = _build_user_message(context, query)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    return _chat(messages, temperature=temperature, max_tokens=max_tokens)


# ------------------------------------------------------------------
# Conversational variant (multi-turn)
# ------------------------------------------------------------------
def generate_response_with_history(
    context: str,
    query: str,
    conversation_history: list[dict],
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Like ``generate_response`` but prepends prior conversation turns."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # Append previous turns (trimmed to last 6 messages to fit context)
    for msg in conversation_history[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "assistant" and len(content) > 500:
            content = content[:500] + "..."
        messages.append({"role": role, "content": content})

    # Final user turn with RAG context
    user_message = _build_user_message(context, query)
    messages.append({"role": "user", "content": user_message})

    return _chat(messages, temperature=temperature, max_tokens=max_tokens)


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
def is_ollama_available() -> bool:
    """Return True if the Ollama server is reachable and the model is pulled."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        if resp.status_code != 200:
            return False
        models = [m["name"] for m in resp.json().get("models", [])]
        # Check if configured model (with or without `:latest` tag) is available
        return any(
            m == OLLAMA_MODEL or m.startswith(f"{OLLAMA_MODEL}:")
            for m in models
        )
    except Exception:
        return False


# ------------------------------------------------------------------
# Internals
# ------------------------------------------------------------------
def _build_user_message(context: str, query: str) -> str:
    """Merge RAG context and query into one user message."""
    if context and context.strip() and not context.startswith("No specific"):
        return (
            f"RELEVANT REFERENCE MATERIAL:\n{context}\n\n"
            f"Using the above reference material where applicable, "
            f"solve the following problem step by step.\n\n"
            f"PROBLEM: {query}"
        )
    return f"Solve the following problem step by step.\n\nPROBLEM: {query}"


def _chat(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """Call the Ollama ``/api/chat`` endpoint (non-streaming)."""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        resp = httpx.post(url, json=payload, timeout=_TIMEOUT)
    except httpx.ConnectError:
        raise OllamaConnectionError(
            f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. "
            "Is Ollama running?  Start it with:  ollama serve"
        )
    except httpx.ReadTimeout:
        raise OllamaGenerationError(
            "Ollama request timed out — the model may be too large for your hardware. "
            "Try a smaller model:  ollama pull llama3"
        )

    if resp.status_code != 200:
        raise OllamaGenerationError(
            f"Ollama returned HTTP {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json()
    content = data.get("message", {}).get("content", "")
    if not content:
        raise OllamaGenerationError("Ollama returned an empty response.")

    logger.info(
        "Ollama generation complete — model=%s, tokens=%s",
        OLLAMA_MODEL,
        data.get("eval_count", "?"),
    )
    return content


# ------------------------------------------------------------------
# Custom exceptions
# ------------------------------------------------------------------
class OllamaConnectionError(RuntimeError):
    """Raised when the Ollama server is unreachable."""


class OllamaGenerationError(RuntimeError):
    """Raised on non-connection generation failures."""
