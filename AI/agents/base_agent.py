from abc import ABC, abstractmethod

from AI.open_ai_client import OpenAiClient


class BaseAgent(ABC):
    """Abstract base class for agents that interact with the OpenAI API."""

    @abstractmethod
    async def create_agent(self, OpenAiClient: OpenAiClient, *args, **kwargs):
        pass

    @abstractmethod
    async def run_agent(self, prompt: str):
        pass