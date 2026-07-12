import asyncio
from dotenv import load_dotenv
from AI.agents.response_agent import ResponseAgent
from AI.open_ai_client import OpenAiClient

load_dotenv()

# Create an instance of OpenAiClient
open_ai_client = OpenAiClient()

# Create an instance of ResponseAgent
agent_name = "Response Agent"
agent_instructions = "You are a helpful assistant that provides responses"
response_agent = ResponseAgent()
response_agent.name = agent_name
response_agent.instructions = agent_instructions
asyncio.run(response_agent.create_agent(open_ai_client))

# Run the mock agent and print the response
response = asyncio.run(response_agent.run_agent("Say hello"))
print(response)        