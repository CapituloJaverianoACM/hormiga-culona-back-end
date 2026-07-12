from agent_framework import Agent
from agent_framework_openai import OpenAIChatClient 
from AI.agents.base_agent import BaseAgent

class ResponseAgent(BaseAgent):
    name = "Response Agent"
    instructions = """
    Eres un asistente de IA que responde la pregunta del usuario basandose en la informacion proporcionada 
    por la query SQL ejecutada por el queryAgent.""" 
    agent: Agent
    async def create_agent(self, OpenAiClient: OpenAIChatClient):
        self.agent = Agent(
            client=OpenAiClient,
            name=self.name,
            instructions=self.instructions
        )

    async def run_agent(self, prompt: str):
        complete_response = await self.agent.run(prompt)
        response = complete_response.text
        return response