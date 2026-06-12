# OCI AI Agent Demo Maintenance Notes

## Project Structure

- `agent/app.py`: FastAPI service entrypoint. It loads environment variables, initializes the OCI-compatible OpenAI client, and creates the lightweight demo agent once at process startup.
- `agent/utils/agui_impl.py`: Converts OpenAI-compatible Responses API stream events into AG-UI protocol events and encodes them for Server-Sent Events.
- `agent/utils/handdler.py`: Pure helper functions for AG-UI input extraction, OpenAI Agents SDK input creation, tool-call field extraction, and serialization.
- `agent/utils/prompt.py`: Agent system instructions.
- `agent/datatype.md`: Local reference for observed OpenAI Agents SDK event ordering and event types.
- `agent/LOG.txt`: Detailed sample stream log. Search this file when adapting event mappings.
- `agent/pyproject.toml`: Python package metadata and dependencies.

## Core Technologies

- FastAPI exposes the AG-UI-compatible HTTP endpoint.
- `ag-ui-protocol` supplies AG-UI event models and `EventEncoder`.
- `AsyncOpenAI` is configured against OCI Generative AI's OpenAI-compatible endpoint.
- The Responses API is used with `x_search` and `code_interpreter` tools.

## Service Flow

1. `app.py` creates one lightweight demo `Agent`.
2. `POST /` accepts `RunAgentInput`.
3. `agui_impl.encoded_response_events(...)` converts AG-UI input into Responses API input, starts the streamed model call, maps stream events to AG-UI events, and returns SSE chunks.
4. The frontend should consume reasoning, tool-call, tool-result, and assistant text events from the SSE stream.

## Coding Rules

- Keep service setup in `agent/app.py`; do not create Agents or MCP servers inside AG-UI event conversion code.
- Keep AG-UI event mapping in `agent/utils/agui_impl.py`; do not add FastAPI or environment loading there.
- Keep low-level extraction and serialization helpers in `agent/utils/handdler.py`.
- Prefer small pure functions for event field extraction because SDK event objects can be pydantic models or dictionaries.
- Ignore empty text deltas before creating AG-UI content events.
- Use `Get-Content -Encoding UTF8` when reading files in PowerShell.
- Use `apply_patch` for manual file edits.
- Prefer `pnpm` for frontend dependency work if frontend code is added later.
- Ask before adding new production dependencies.

## Environment

Required variables live in the root `.env`; use `.env.example` as the public template:

- `AGENT_MODEL_ID`
- `AGENT_NAME`
- `OCI_GENAI_BASE_URL`
- `OCI_GENAI_KEY`

Do not commit real secrets in `.env`; use local or deployment-specific secret management.

## Verification

When testing is allowed, start with:

- `uv run python -m py_compile .\app.py .\utils\agui_impl.py .\utils\handdler.py` from `agent/`
- `uv run uvicorn app:app --host 127.0.0.1 --port 8001` from `agent/`

Then send an AG-UI `RunAgentInput` request to `POST /` and confirm the stream includes `RUN_STARTED`, reasoning events, optional tool-call events, assistant text events, and `RUN_FINISHED`.
