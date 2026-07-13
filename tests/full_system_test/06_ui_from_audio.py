import json
from pathlib import Path

import requests

base = "http://127.0.0.1:8000"
out_dir = Path("tests/full_system_test/artifacts")
out_dir.mkdir(parents=True, exist_ok=True)

spoken_text = "Haz un reporte simple de gastos por año"

audio_response = requests.post(f"{base}/agent/audio/synthesis", json={"text": spoken_text}, timeout=180)
audio_response.raise_for_status()
audio_bytes = audio_response.content
assert audio_bytes
(out_dir / "06_ui_question.wav").write_bytes(audio_bytes)

transcription_response = requests.post(
    f"{base}/agent/audio/transcription",
    files={"file": ("06_ui_question.wav", audio_bytes, "audio/wav")},
    timeout=180,
)
transcription_response.raise_for_status()
transcription = transcription_response.json()
question = transcription["text"].strip()
assert question
(out_dir / "06_ui_transcription.json").write_text(json.dumps(transcription, ensure_ascii=False, indent=2), encoding="utf-8")

ui_response = requests.post(
    f"{base}/agent/ui",
    json={"content": question, "preview_limit": 5},
    timeout=180,
)
ui_response.raise_for_status()
ui_data = ui_response.json()
assert ui_data["sql"].strip()
assert isinstance(ui_data["rows"], list)
assert isinstance(ui_data["preview_rows"], list)
assert isinstance(ui_data["columns"], list)
(out_dir / "06_ui_response.json").write_text(json.dumps(ui_data, ensure_ascii=False, indent=2), encoding="utf-8")
print({"title": ui_data.get("title"), "component": ui_data.get("component"), "row_count": ui_data.get("row_count")})
