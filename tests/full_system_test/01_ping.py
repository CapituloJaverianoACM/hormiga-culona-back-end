import requests

response = requests.get("http://127.0.0.1:8000/ping", timeout=30)
response.raise_for_status()
data = response.json()
assert data["status"] == "ok"
assert data["message"] == "pong"
print(data)
