import json
from pathlib import Path

import requests

base = "http://127.0.0.1:8000"
out_dir = Path("tests/full_system_test/artifacts")
out_dir.mkdir(parents=True, exist_ok=True)

spoken_text = "Hola dime los gastos de 2017"

audio_response = requests.post(f"{base}/agent/audio/synthesis", json={"text": spoken_text}, timeout=180)
audio_response.raise_for_status()
audio_bytes = audio_response.content
assert audio_bytes
(out_dir / "05_chat_question.wav").write_bytes(audio_bytes)

transcription_response = requests.post(
    f"{base}/agent/audio/transcription",
    files={"file": ("05_chat_question.wav", audio_bytes, "audio/wav")},
    timeout=180,
)
transcription_response.raise_for_status()
transcription = transcription_response.json()
question = transcription["text"].strip()
assert question
(out_dir / "05_chat_transcription.json").write_text(json.dumps(transcription, ensure_ascii=False, indent=2), encoding="utf-8")

chat_response = requests.post(
    f"{base}/agent/chat",
    json={"content": question, "sender_id": "full-system-test-chat"},
    timeout=180,
)
chat_response.raise_for_status()
chat_data = chat_response.json()
assert chat_data["voice_reply"].strip()
assert chat_data["explanation"].strip()
assert isinstance(chat_data, dict)
(out_dir / "05_chat_response.json").write_text(json.dumps(chat_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(chat_data)
