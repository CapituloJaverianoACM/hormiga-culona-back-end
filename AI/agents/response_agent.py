from agent_framework import Agent
from agent_framework_openai import OpenAIChatClient 
from AI.agents.base_agent import BaseAgent

class ResponseAgent(BaseAgent):
    name: str
    instructions: str
    agent: Agent
    async def create_agent(self, OpenAiClient: OpenAIChatClient):
        self.agent = Agent(
            client=OpenAiClient,
            name=self.name,
            instructions=self.instructions
        )

    async def run_agent(self, prompt: str):
        response = await self.agent.run(prompt)
        return response