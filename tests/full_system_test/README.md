# full_system_test

Simple live endpoint scripts.

Rules used here:
- no imports from app code
- no shared helpers
- only real HTTP/WebSocket endpoints
- audio flows use `/agent/audio/synthesis` + `/agent/audio/transcription`
- keep each script standalone and small

## Preconditions
- server running on `http://127.0.0.1:8000`
- `.env` configured
- DB reachable
- Azure speech working

## Run all

```bash
bash tests/full_system_test/run_all.sh
```

## Run one script

```bash
python tests/full_system_test/01_ping.py
python tests/full_system_test/06_chat_from_audio.py
python tests/full_system_test/10_ws_audio_both.py
```
