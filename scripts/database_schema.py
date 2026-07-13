"""
Tool used before the agent is created to get the database schema
"""
import requests


"""
curl -X 'GET' \
  'http://127.0.0.1:8000/agent/description' \
  -H 'accept: application/json'
"""

def sql_schema() -> dict:
    """
    Sends a request to the specified API endpoint to get the database schema.

    Returns:
        dict: The JSON response from the API.
    """
    url = "http://127.0.0.1:8000/agent/description"
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")