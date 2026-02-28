"""
Chat service: ephemeral AI session + save/restore from blockchain.
- In-memory conversation only; after session end we summarize, encrypt, push to chain and "delete" the AI (clear state).
- On new session we pull summaries from chain, decrypt, and feed as context to a fresh AI.
"""
from app.crypto import encrypt_for_user, decrypt_for_user
from app.blockchain import get_chain_store
from app.blockchain.base import BlockRecord
from app.ai_client import chat, summarize_for_storage


# No persistent in-memory state across requests; each request can carry session_id + in-session messages.
# "Ephemeral" means: we don't keep the AI model or full history on server after we've persisted to chain.


def build_context_from_summaries(decrypted_summaries: list[str]) -> str:
    """Turn decrypted summary texts into one context block for the AI system message."""
    if not decrypted_summaries:
        return ""
    return (
        "Previous conversation summaries (for context only):\n\n"
        + "\n\n---\n\n".join(decrypted_summaries)
    )


def get_restored_context(user_id: str, user_secret: str) -> str:
    """
    Load all blocks for user from chain, decrypt block by block, return combined context string.
    """
    store = get_chain_store()
    blocks = store.get_blocks(user_id)
    summaries = []
    for block in blocks:
        try:
            payload_bytes = bytes.fromhex(block.payload_hex)
            dec = decrypt_for_user(payload_bytes, user_secret)
            summaries.append(dec.decode("utf-8"))
        except Exception:
            continue
    return build_context_from_summaries(summaries)


def save_session_to_chain(
    user_id: str,
    user_secret: str,
    messages: list[dict],
    max_summary_words: int = 3000,
) -> BlockRecord:
    """
    Summarize current chat, encrypt with user secret, store one block on chain.
    Call this when ending a session; then discard messages (ephemeral AI "deleted").
    """
    summary = summarize_for_storage(messages, max_words=max_summary_words)
    if not summary:
        raise ValueError("No content to summarize")
    payload = encrypt_for_user(summary, user_secret)
    payload_hex = payload.hex()
    store = get_chain_store()
    next_seq = store.get_latest_sequence(user_id) + 1
    return store.store_block(user_id, next_seq, payload_hex)


def chat_turn(
    user_id: str,
    user_secret: str,
    user_message: str,
    session_messages: list[dict],
    model: str = "gpt-4o-mini",
) -> tuple[str, list[dict]]:
    """
    One chat turn. session_messages is the in-memory history for this session only.
    We prepend restored context from chain as system context.
    Returns (assistant_reply, updated_session_messages).
    """
    context = get_restored_context(user_id, user_secret)
    system_content = (
        "You are a supportive, confidential AI friend. The user may share personal or sensitive information; "
        "keep it private and never repeat it outside this conversation. "
    )
    if context:
        system_content += "\n\n" + context

    messages = [{"role": "system", "content": system_content}]
    messages.extend(session_messages)
    messages.append({"role": "user", "content": user_message})

    reply = chat(messages, model=model)
    new_history = session_messages + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply},
    ]
    return reply, new_history
