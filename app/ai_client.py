"""
AI client for chat and summarization (OpenAI-compatible API).
Ephemeral: no history is persisted in the AI provider; we only use it for one session.
"""
from openai import OpenAI
from config import settings


def get_client() -> OpenAI:
    return OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )


def chat(messages: list[dict], model: str = "gpt-4o-mini") -> str:
    """Send messages to the model and return the assistant reply text."""
    client = get_client()
    r = client.chat.completions.create(model=model, messages=messages)
    return (r.choices[0].message.content or "").strip()


def summarize_for_storage(messages: list[dict], model: str = "gpt-4o-mini", max_words: int = 3000) -> str:
    """
    Condense chat history into a single summary (thousands of words) for encrypted storage.
    The summary should preserve context so a new AI can continue the "same" conversation.
    """
    client = get_client()
    # Build a single transcript string for the summarizer
    lines = []
    for m in messages:
        role = m.get("role", "unknown")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role.upper()}: {content}")
    transcript = "\n\n".join(lines)
    if not transcript.strip():
        return ""

    system = (
        "You are a summarization assistant. Your task is to condense a chat transcript "
        f"into a single coherent summary of at most {max_words} words. "
        "Preserve: key facts, decisions, emotional tone, important details the user shared, "
        "and context that would let a future AI continue the same relationship. "
        "Write in third person or neutral narrative. Output only the summary, no preamble."
    )
    user_msg = f"Summarize this chat transcript:\n\n{transcript}"
    summary = chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
        model=model,
    )
    return summary.strip()
