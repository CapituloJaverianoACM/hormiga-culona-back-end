import json
from pathlib import Path

import requests
import websockets.sync.client

base = "http://127.0.0.1:8000"
out_dir = Path("tests/full_system_test/artifacts")
out_dir.mkdir(parents=True, exist_ok=True)
url = "ws://127.0.0.1:8000/ws/agent/voice/full-system-text-audio?mode=response&output=audio&preview_limit=5"

with websockets.sync.client.connect(url, open_timeout=30, close_timeout=10, max_size=None) as ws:
    ws.send("Dame un resumen breve de los gastos")
    audio_bytes = ws.recv(timeout=180)
    assert isinstance(audio_bytes, (bytes, bytearray))
    audio_bytes = bytes(audio_bytes)

assert audio_bytes
(out_dir / "08_ws_text_audio.wav").write_bytes(audio_bytes)

transcription_response = requests.post(
    f"{base}/agent/audio/transcription",
    files={"file": ("08_ws_text_audio.wav", audio_bytes, "audio/wav")},
    timeout=180,
)
transcription_response.raise_for_status()
transcription = transcription_response.json()
assert transcription["text"].strip()
(out_dir / "08_ws_text_audio_transcription.json").write_text(json.dumps(transcription, ensure_ascii=False, indent=2), encoding="utf-8")
print(transcription)
