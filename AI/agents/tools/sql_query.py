import requests
from agent_framework import tool

"""
Tool for querying a SQL database using an API endpoint.

curl -X 'POST' \
  'http://127.0.0.1:8000/agent/sql' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "sql_query": "string"
}'
}'

"""
@tool(approval_mode="never_require")
def sql_query(
    sql_query: str
) -> dict:
    """
    Sends a SQL query to the specified API endpoint and returns the response.

    Args:
        sql_query (str): The SQL query to be executed.
    Returns:
        dict: The JSON response from the API.
    """
    url = "http://127.0.0.1:8000/agent/sql"
    payload = {
        "sql_query": sql_query
    }
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")