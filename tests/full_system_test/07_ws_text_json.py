import json
from pathlib import Path

import websockets.sync.client

out_dir = Path("tests/full_system_test/artifacts")
out_dir.mkdir(parents=True, exist_ok=True)
url = "ws://127.0.0.1:8000/ws/agent/voice/full-system-text-json?mode=response&output=json&preview_limit=5"

with websockets.sync.client.connect(url, open_timeout=30, close_timeout=10, max_size=None) as ws:
    ws.send("Hola dime los gastos de 2017")
    message = ws.recv(timeout=180)
    assert isinstance(message, str)
    data = json.loads(message)

assert data["type"] == "agent_result"
assert data["mode"] == "response"
assert data["voice_reply"].strip()
assert data["explanation"].strip()
assert isinstance(data["data"], dict)
assert "rows" not in data["data"]
(out_dir / "07_ws_text_json.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(data)
