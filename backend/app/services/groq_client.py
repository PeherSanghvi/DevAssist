"""Groq streaming client. Raises typed errors the WS handler maps to codes."""
import asyncio
import os


class GroqNotConfigured(Exception):
    pass


class GroqRateLimited(Exception):
    pass


class GroqProviderError(Exception):
    pass


async def stream_chat(messages: list[dict], model: str):
    """Async generator yielding text tokens. Real Groq SDK, streamed.

    The synchronous SDK streaming iterator runs in a thread so it never
    blocks the event loop. Tests monkeypatch this function; production
    code must never substitute fake tokens here.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise GroqNotConfigured("Groq API key is not configured on the server.")

    def _run():
        from groq import Groq

        client = Groq(api_key=api_key)
        stream = client.chat.completions.create(model=model, messages=messages, stream=True)
        tokens = []
        for event in stream:
            delta = event.choices[0].delta.content if event.choices else None
            if delta:
                tokens.append(delta)
        return tokens

    try:
        tokens = await asyncio.to_thread(_run)
    except Exception as exc:  # map SDK errors to stable codes
        name = type(exc).__name__
        msg = str(exc)
        if name == "RateLimitError" or "rate limit" in msg.lower() or "429" in msg:
            raise GroqRateLimited("Groq rate limit reached. Please wait a moment and retry.")
        if name in ("APITimeoutError", "APIConnectionError") or "timed out" in msg.lower():
            raise GroqProviderError("The AI provider timed out. Please retry.")
        raise GroqProviderError("The AI provider returned an unexpected error. Please retry.")
    for tok in tokens:
        yield tok
