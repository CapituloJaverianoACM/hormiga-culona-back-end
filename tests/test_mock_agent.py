import os
import asyncio
from dotenv import load_dotenv
from AI.agents.mock_agent import mockAgent
from AI.open_ai_client import OpenAiClient

load_dotenv()

# Create an instance of OpenAiClient
open_ai_client = OpenAiClient()

# Create an instance of mockAgent
agent_name = "Mock Agent"
agent_instructions = "This is a mock agent for testing purposes."
mock_agent = mockAgent()
asyncio.run(mock_agent.create_agent())

# Run the mock agent and print the response
response = asyncio.run(mock_agent.run_agent("test"))
print(response)