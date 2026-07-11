import asyncio
from dotenv import load_dotenv
from AI.agents.query_agent import queryAgent
from AI.open_ai_client import OpenAiClient

load_dotenv()

# Create an instance of OpenAiClient
open_ai_client = OpenAiClient()

# Create an instance of queryAgent
agent_name = "Query Agent"
agent_instructions = "This is a query agent for testing purposes."
query_agent = queryAgent()
query_agent.name = agent_name
query_agent.instructions = agent_instructions
asyncio.run(query_agent.create_agent(open_ai_client))

# Run the mock agent and print the response
response = asyncio.run(query_agent.run_agent("Give me an example of a query in sql."))
print(response)