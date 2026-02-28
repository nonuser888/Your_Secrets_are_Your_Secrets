# YourSecret — Secure AI Chat

A secure tool for talking to an AI agent so that **user secrets are not leaked**. Flow:

1. **While chatting**: You talk to an AI model; conversation stays in memory only for that session.
2. **On session end**: The chat history is **summarized** (condensed to a configurable length, e.g. thousands of words), **encrypted** with your secret, and **saved as a block** on a blockchain (Abelian or a local file-based store).
3. **AI is then “deleted”**: The in-session conversation is discarded; no full history is kept on the server.
4. **Next time**: When you talk to the “same” AI friend again, the app **retrieves** your summary blocks from the blockchain, **decrypts** them block by block with your secret, and **feeds** that context to a **new** AI instance.

So: only **encrypted summaries** live on the chain; the **raw chat and the AI** are ephemeral.

## Features

- **Encryption**: Summaries are encrypted with a key derived from your secret (e.g. password). Only you can decrypt.
- **Blockchain storage**: Optional **Abelian** integration; without it, a **file-based** store simulates blocks under `./data/chain`.
- **Ephemeral AI**: No long-lived AI state; after saving to the chain, the session is cleared.

---

## How to run (detailed)

### 1. Prerequisites

- **Python 3.10 or newer** (check with `python3 --version`).
- **OpenAI API key** (or another OpenAI-compatible API key) for chat and summarization.

### 2. Open a terminal and go to the project folder

```bash
cd /home/yourUserName/yourSecret_v0
```

(Use your actual path to `yourSecret_v0` if it’s different.)

### 3. Create a virtual environment

This keeps the project’s dependencies separate from the rest of your system.

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt):**

```cmd
py -3 -m venv .venv
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

When the venv is active, your prompt usually starts with `(.venv)`.

### 4. Install dependencies

Still in the same terminal, with the venv activated:

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Copy the example env file and edit it:

```bash
cp .env.example .env
```

Edit `.env` (e.g. with Notepad, VS Code, or `nano .env`). You **must** set:

- **`OPENAI_API_KEY`**  
  Your OpenAI API key (e.g. `sk-proj-...`).  
  If you use a different provider (e.g. Azure, local model), set **`OPENAI_BASE_URL`** too (e.g. `https://api.openai.com/v1` or your provider’s URL).

Leave the Abelian variables empty to use the **local file-based “blockchain”** (no Abelian node needed). Example minimal `.env`:

```env
OPENAI_API_KEY=sk-your-real-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 6. Start the server

With the venv still active:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **`--reload`**: restarts the server when you change code (optional; omit in production).
- **`--host 0.0.0.0`**: allows access from other devices on your network (use `127.0.0.1` for local-only).
- **`--port 8000`**: serve on port 8000.

You should see something like:

```text
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Leave this terminal open while you use the app.

### 7. Use the API

- **Interactive docs (Swagger):**  
  Open in a browser: **http://localhost:8000/docs**  
  You can try `GET /health`, then `POST /session/start`, `POST /chat`, and `POST /session/end` from there.

- **Quick checks in terminal** (in a **second** terminal, same machine):

```bash
# Health check
curl http://localhost:8000/health

# Start a session (copy the session_id from the response)
curl -X POST http://localhost:8000/session/start

# Send a message (replace SESSION_ID and use your own user_id / user_secret / message)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"SESSION_ID","user_id":"alice","user_secret":"my-secret-password","message":"Hello, remember this: my cat is named Bob."}'

# End session (saves summary to chain and deletes in-memory history)
curl -X POST http://localhost:8000/session/end \
  -H "Content-Type: application/json" \
  -d '{"session_id":"SESSION_ID","user_id":"alice","user_secret":"my-secret-password"}'
```

Use the **same `session_id`** for all requests in one conversation, and the **same `user_id` and `user_secret`** every time you want the “same” AI friend (so the app can decrypt your stored summaries).

### 8. Stop the server

In the terminal where uvicorn is running, press **Ctrl+C**.

---

## Short version (setup + run)

```bash
cd yourSecret_v0
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

## API usage

1. **Start session**  
   `POST /session/start`  
   Returns a `session_id`.

2. **Chat**  
   `POST /chat`  
   Body: `session_id`, `user_id`, `user_secret`, `message`.  
   Each call uses context restored from the chain (decrypted with `user_secret`) and appends to in-memory session history.

3. **End session**  
   `POST /session/end`  
   Body: `session_id`, `user_id`, `user_secret`.  
   Summarizes the conversation, encrypts it, stores one block on the chain, then discards the session (ephemeral AI “deleted”).

## Configuration

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | API key for an OpenAI-compatible chat API. |
| `OPENAI_BASE_URL` | Base URL (default: OpenAI). |
| `ABELIAN_RPC_URL` | Abelian node RPC URL (e.g. `https://node:8667`). If unset, file-based store is used. |
| `ABELIAN_RPC_USER` / `ABELIAN_RPC_PASS` | RPC credentials. |
| `ABELIAN_WALLET_RPC_URL` | Optional; wallet RPC for creating/sending transactions with data. |
| `LOCAL_CHAIN_DIR` | Directory for file-based “chain” when Abelian is not configured (default: `./data/chain`). |

## Abelian blockchain

- **Storage**: Encrypted payloads are stored in transaction data outputs (OP_RETURN-style) on Abelian when RPC is configured.
- **Retrieval**: With the file-based store, blocks are indexed by `user_id`. With Abelian, you may need to maintain your own index of block/tx IDs per user (e.g. in your app DB) and use `get_block_by_id` to fetch payloads by tx hash.
- **Docs**: [Abelian Community API](https://community.pqabelian.io/apis/core-api), [Java SDK](https://github.com/pqabelian/abelian-sdk-java-v2).

## Security notes

- **User secret**: Never log or store `user_secret`; it is only used to derive the encryption key and decrypt summaries.
- **TLS**: Use HTTPS in production; for Abelian RPC use TLS (e.g. `rpc.cert`).
- **Session store**: The in-memory `_sessions` is for demo; in production use short-lived tokens or Redis and clear after `/session/end`.

## License

MIT.
