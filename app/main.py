"""
API for secure AI chat: secrets encrypted and stored on blockchain; AI is ephemeral.
"""
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.chat_service import chat_turn, save_session_to_chain

app = FastAPI(
    title="YourSecret",
    description="Secure AI chat: history summarized, encrypted, and stored on blockchain; AI instance is deleted after session.",
)

# In-memory session store: session_id -> list of messages for this session only.
# In production use Redis or short-lived tokens; server still does not persist after "end session".
_sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Current session id (create new with start_session)")
    user_id: str = Field(..., description="Stable user identifier")
    user_secret: str = Field(..., description="User's secret for encryption (e.g. password)")
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class StartSessionResponse(BaseModel):
    session_id: str


class EndSessionRequest(BaseModel):
    session_id: str
    user_id: str
    user_secret: str


class EndSessionResponse(BaseModel):
    block_id: str
    sequence: int
    message: str = "Session saved to blockchain. AI state discarded."


@app.post("/session/start", response_model=StartSessionResponse)
def start_session():
    """Start a new ephemeral chat session. History is only in memory until you end the session."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = []
    return StartSessionResponse(session_id=session_id)


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """
    Send a message to the AI. Context is restored from blockchain (decrypted with user_secret).
    The AI is stateless per request; session history is kept in memory for this session only.
    """
    if req.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Call /session/start first.")
    messages = _sessions[req.session_id]
    reply, new_messages = chat_turn(
        user_id=req.user_id,
        user_secret=req.user_secret,
        user_message=req.message,
        session_messages=messages,
    )
    _sessions[req.session_id] = new_messages
    return ChatResponse(reply=reply, session_id=req.session_id)


@app.post("/session/end", response_model=EndSessionResponse)
def end_session(req: EndSessionRequest):
    """
    Summarize chat history (thousands of words), encrypt with user_secret,
    store one block on blockchain, then delete the in-session AI state (clear messages).
    """
    if req.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    messages = _sessions[req.session_id]
    if not messages:
        raise HTTPException(status_code=400, detail="No messages to save.")
    try:
        record = save_session_to_chain(
            user_id=req.user_id,
            user_secret=req.user_secret,
            messages=messages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save to chain: {e}") from e
    del _sessions[req.session_id]
    return EndSessionResponse(
        block_id=record.block_id,
        sequence=record.sequence,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
