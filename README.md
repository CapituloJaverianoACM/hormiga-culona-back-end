# hormiga-culona-back-end

Backend FastAPI para chat, UI y voz sobre consultas SQL.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Variables mínimas en `.env`:
- `DATABASE_URL`
- `FOUNDRY_PROJECT_ENDPOINT`
- `FOUNDRY_MODEL_DEPLOYMENT_NAME`
- `AZURE_AI_FOUNDRY_API_KEY`
- `AZURE_SPEECH_ENDPOINT`
- `AZURE_SPEECH_API_KEY`

## Run server

```bash
uvicorn main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/ping
```

## HTTP endpoints

- `POST /agent/chat`
- `POST /agent/ui`
- `POST /agent/audio/transcription`
- `POST /agent/audio/synthesis`
- `GET /agent/description`

## WebSocket voice protocol

Endpoint:

```text
ws://127.0.0.1:8000/ws/agent/voice/{session_id}?mode=response|ui&output=audio|json|both&preview_limit=5
```

Query params:
- `mode=response|ui`
- `output=audio|json|both`
- `preview_limit=1..20`

Frame types:
- client can send a **text frame** with the user prompt
- client can send a **bytes frame** with audio wav payload
- server can return a **text frame** with JSON when `output=json|both`
- server can return a **bytes frame** with synthesized audio when `output=audio|both`

JSON payload shape returned by websocket:

```json
{
  "type": "agent_result",
  "mode": "response",
  "user_text": "hola",
  "voice_reply": "respuesta corta",
  "explanation": "explicación breve",
  "data": {}
}
```

## Run tests

Simple pytest run:

```bash
pytest -q
```

Roundtrip websocket test:

```bash
python tests/audio/test_roundtrip.py --mode response --output both
```

Useful variants:

```bash
python tests/audio/test_roundtrip.py --mode ui --output json
python tests/audio/test_roundtrip.py --prompt "Hola dime los gastos de 2017" --mode response --output both
```

Artifacts from the roundtrip test are written to `tests/audio/artifacts/` and ignored by git.
