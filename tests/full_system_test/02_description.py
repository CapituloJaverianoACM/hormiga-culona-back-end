import requests

response = requests.get("http://127.0.0.1:8000/agent/description", timeout=60)
response.raise_for_status()
data = response.json()
assert data is not None
print(type(data).__name__)
print(data)
