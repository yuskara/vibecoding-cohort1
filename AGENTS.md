# AGENTS.md — Repository Guidelines for Healing KB

## MANDATORY RULE: Always Update These Files

**After every code change, update `CONTINUE.md` and `AGENTS.md` before committing.**

Update the relevant sections in the following cases:

| Change | Update |
|---|---|
| New module / file added | "Project Structure" section in both files |
| New API endpoint | `CONTINUE.md` endpoint table + routing section in this file |
| New frontend page | `CONTINUE.md` architecture table + structure section in this file |
| New `pip` dependency | Dependencies section in this file |
| New environment variable | Relevant notes in both files |

Committing without updating these files is prohibited.

---

## Project Structure

```
app.py                  # Flask application; routing, validation, session management for Healing KB
llm.py                  # OpenAI/Ollama client; stateless stream_llm() function for wellness queries
asistan.py              # Assistant class; conversation history + stream_sohbet() for user interactions
agent.py                # Agent class; tool-calling agentic loop + calistir() generator for wellness analysis. Includes `search_supabase` to query Supabase healing knowledge base.
frontend/
  index.html            # LLM interface: single prompt/response page for quick wellness insights
  asistan.html          # Assistant interface: multi-turn, bubble chat for guided healing conversations
  agent.html            # Agent interface: visual display of tool calls and steps for trauma analysis
requirements.txt        # Python dependencies
.env                    # Local secrets (not committed); OPENAI_API_KEY / OLLAMA_API_BASE here
CONTINUE.md             # Architectural guidance for CONTINUE Code
AGENTS.md               # This file; developer and agent rules for Healing KB
```

Backend routing and validation stays in `app.py`. Provider-specific LLM calls in `llm.py`, `asistan.py`, or `agent.py`. Static files under `frontend/`. Currently configured to use local Ollama with `qwen2.5-coder:7b` model.

---

## API Endpoints

| Method | Path | Body | Description |
|---|---|---|---|
| POST | `/api/chat` | `{model, system_instructions, user_prompt}` | Stateless, one-time LLM call (streaming, text/plain) for wellness queries |
| POST | `/api/asistan/yeni` | `{model, system_instructions}` | Creates new assistant session, returns `session_id` for healing guidance |
| POST | `/api/asistan/sohbet` | `{session_id, user_prompt}` | Sends message to assistant (streaming, text/plain) for ongoing support |
| POST | `/api/agent/yeni` | `{model, system_instructions}` | Creates new agent session, returns `session_id` for trauma analysis |
| POST | `/api/agent/calistir` | `{session_id, user_prompt}` | Runs agent (NDJSON stream; event types: `step_start`, `thinking`, `tool_call`, `tool_result`, `text`, `done`, `error`) for deep insights |

---

## Development Commands

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug   # http://127.0.0.1:5000
```

---

## Code Style

- Python 3, 4-space indentation, type hints for reusable helpers.
- Follow `stream_llm(...) -> Iterator[str]` and `stream_sohbet(...) -> Iterator[str]` signatures.
- Error messages should be user-friendly if API limits are exceeded, hide provider errors.
- Frontend: simple HTML/CSS/JS, `camelCase` JS variables, purpose-appropriate `id` names.

---

## Testing Guide

Automated test suite not present. If adding tests:

- Create `tests/` directory, use `pytest`.
- Name files as `test_*.py`.
- Priority test areas: Flask route validation, `ALLOWED_MODELS` check, streaming error handling, assistant history validation.

```sh
pytest
```

For frontend changes, manually verify in browser: empty prompt prevention, model selection, streaming render, assistant history continuity.

---

## Commit and PR Rules

- Commit messages short and imperative: `Add streaming assistant`, `Validate chat payload`.
- PRs: short summary, test notes, required `.env` changes, screenshot if UI changes.

---

## Security

- API keys only in `.env`; load with `python-dotenv`. Do not commit.
- Forbidden to leak secrets in logs or API responses.
- Update `app.py` and all frontend `<select>` elements together when `ALLOWED_MODELS` changes.
- `_asistanlar` dict in server memory; need persistent storage for production.
