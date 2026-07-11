from agent_framework import Agent
from AI.open_ai_client import OpenAiClient
from AI.agents.base_agent import BaseAgent

class mockAgent(BaseAgent):
    name: str
    instructions: str
    agent: Agent
    async def create_agent(self):
        pass

    async def run_agent(self, prompt: str):
        response = "This is a mock response from the mock agent."
        return response