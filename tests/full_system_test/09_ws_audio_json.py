import json
from pathlib import Path

import requests
import websockets.sync.client

base = "http://127.0.0.1:8000"
out_dir = Path("tests/full_system_test/artifacts")
out_dir.mkdir(parents=True, exist_ok=True)
spoken_text = "Hazme un reporte de gastos por año"

synth = requests.post(f"{base}/agent/audio/synthesis", json={"text": spoken_text}, timeout=180)
synth.raise_for_status()
audio_bytes = synth.content
assert audio_bytes
(out_dir / "09_ws_audio_json_question.wav").write_bytes(audio_bytes)

trans = requests.post(
    f"{base}/agent/audio/transcription",
    files={"file": ("09_ws_audio_json_question.wav", audio_bytes, "audio/wav")},
    timeout=180,
)
trans.raise_for_status()
question = trans.json()["text"].strip()
assert question

url = "ws://127.0.0.1:8000/ws/agent/voice/full-system-audio-json?mode=ui&output=json&preview_limit=5"
with websockets.sync.client.connect(url, open_timeout=30, close_timeout=10, max_size=None) as ws:
    ws.send(audio_bytes)
    message = ws.recv(timeout=180)
    assert isinstance(message, str)
    data = json.loads(message)

assert data["type"] == "agent_result"
assert data["mode"] == "ui"
assert data["user_text"].strip()
assert data["data"]["sql"].strip()
assert isinstance(data["data"]["rows"], list)
(out_dir / "09_ws_audio_json_response.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print({"user_text": data["user_text"], "row_count": data["data"].get("row_count")})
