from abc import ABC, abstractmethod

from AI.open_ai_client import OpenAiClient


class BaseAgent(ABC):
    """Abstract base class for agents that interact with the OpenAI API."""

    def inject_prompt(self, prompt: str) -> str:
        clean_prompt = (prompt or "").strip()
        return f"Solicitud del usuario:\n{clean_prompt}\n\nResponde usando esta solicitud como la tarea principal.".strip()

    @abstractmethod
    async def create_agent(self, OpenAiClient: OpenAiClient, *args, **kwargs):
        pass

    @abstractmethod
    async def run_agent(self, prompt: str):
        pass