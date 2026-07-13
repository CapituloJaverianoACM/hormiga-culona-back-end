import json
from pathlib import Path

import requests

base = "http://127.0.0.1:8000"
out_dir = Path("tests/full_system_test/artifacts")
out_dir.mkdir(parents=True, exist_ok=True)

text = "Hola dime los gastos de 2017"

synth = requests.post(f"{base}/agent/audio/synthesis", json={"text": text}, timeout=180)
synth.raise_for_status()
assert synth.headers.get("content-type", "").startswith("audio/")
audio_bytes = synth.content
assert audio_bytes
(audio_path := out_dir / "03_audio.wav").write_bytes(audio_bytes)

trans = requests.post(
    f"{base}/agent/audio/transcription",
    files={"file": ("03_audio.wav", audio_bytes, "audio/wav")},
    timeout=180,
)
trans.raise_for_status()
data = trans.json()
assert data["text"].strip()
(out_dir / "03_transcription.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(data)
