import asyncio
import os
import dotenv
from agent_framework import Agent
from agent_framework_openai import OpenAIChatClient 

class OpenAiClient(OpenAIChatClient):
    def __init__(self):
        """Initialize the OpenAiClient with environment variables."""
        dotenv.load_dotenv()
        self.base_url = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
        self.model = os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME")
        self.api_key = os.getenv("AZURE_AI_FOUNDRY_API_KEY")
        super().__init__(base_url=self.base_url, model=self.model, api_key=self.api_key)