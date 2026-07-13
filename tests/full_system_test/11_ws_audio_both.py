import json
from pathlib import Path

import requests
import websockets.sync.client

base = "http://127.0.0.1:8000"
out_dir = Path("tests/full_system_test/artifacts")
out_dir.mkdir(parents=True, exist_ok=True)
spoken_text = "Hola dime los gastos de 2017"

synth = requests.post(f"{base}/agent/audio/synthesis", json={"text": spoken_text}, timeout=180)
synth.raise_for_status()
audio_bytes = synth.content
assert audio_bytes
(out_dir / "11_ws_audio_both_question.wav").write_bytes(audio_bytes)

url = "ws://127.0.0.1:8000/ws/agent/voice/full-system-audio-both?mode=response&output=both&preview_limit=5"
with websockets.sync.client.connect(url, open_timeout=30, close_timeout=10, max_size=None) as ws:
    ws.send(audio_bytes)

    message = ws.recv(timeout=180)
    assert isinstance(message, str)
    data = json.loads(message)

    response_audio = ws.recv(timeout=180)
    assert isinstance(response_audio, (bytes, bytearray))
    response_audio = bytes(response_audio)

assert data["type"] == "agent_result"
assert data["mode"] == "response"
assert data["voice_reply"].strip()
assert isinstance(data["data"], dict)
assert "rows" not in data["data"]
assert response_audio

(out_dir / "11_ws_audio_both_response.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
(out_dir / "11_ws_audio_both_response.wav").write_bytes(response_audio)

trans = requests.post(
    f"{base}/agent/audio/transcription",
    files={"file": ("11_ws_audio_both_response.wav", response_audio, "audio/wav")},
    timeout=180,
)
trans.raise_for_status()
transcription = trans.json()
spoken_text = transcription["text"].strip()
assert spoken_text
assert "json" not in spoken_text.lower()
assert "son" not in spoken_text.lower()
(out_dir / "11_ws_audio_both_transcription.json").write_text(json.dumps(transcription, ensure_ascii=False, indent=2), encoding="utf-8")
print({"voice_reply": data["voice_reply"], "spoken": transcription["text"]})
