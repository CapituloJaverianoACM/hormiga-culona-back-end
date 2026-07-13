import json
from pathlib import Path

import requests

base = "http://127.0.0.1:8000"
out_dir = Path("tests/full_system_test/artifacts")
out_dir.mkdir(parents=True, exist_ok=True)

payload = {"sql_query": "SELECT 1 AS ok"}
response = requests.post(f"{base}/agent/sql", json=payload, timeout=60)
response.raise_for_status()
data = response.json()
assert data["status"] == "success"
assert isinstance(data["data"], list)
(out_dir / "04_sql_http.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(data)
