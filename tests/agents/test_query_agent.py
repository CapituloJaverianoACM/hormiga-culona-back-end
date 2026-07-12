import asyncio
from dotenv import load_dotenv
from AI.agents.query_agent import queryAgent
from AI.open_ai_client import OpenAiClient
from scripts.database_squema import sql_schema

load_dotenv()

# get the database schema
database_schema = sql_schema()

# Create an instance of OpenAiClient
open_ai_client = OpenAiClient()

# Create an instance of queryAgent
query_agent = queryAgent()
asyncio.run(query_agent.create_agent(open_ai_client, database_schema))

# Run the mock agent and print the response
response = asyncio.run(query_agent.run_agent("podrias hacer una query que me diga la primera fila de las 2 bases de datos?"))
print(response)