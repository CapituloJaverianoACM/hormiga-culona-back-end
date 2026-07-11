from abc import ABC, abstractmethod
from agent_framework import Agent
from AI.open_ai_client import OpenAiClient

class BaseAgent(ABC):
    @abstractmethod
    async def create_agent(self, OpenAiClient: OpenAiClient, name :str, instructions: str):
        pass

    @abstractmethod
    async def run_agent(self, prompt: str):
        pass