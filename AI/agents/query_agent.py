from agent_framework import Agent
from agent_framework_openai import OpenAIChatClient

from AI.agents.base_agent import BaseAgent
from AI.agents.tools.sql_query import sql_query


class queryAgent(BaseAgent):
    """"
    queryAgent is an agent that answers user questions using SQL queries."""
    name = "Query Agent"
    instructions = """
    Eres un asistente de IA que responde preguntas del usuario usando SQL.
    Usa la tool sql_query para ejecutar consultas de solo lectura y responder con lenguaje natural.
    No inventes datos. Si la consulta falla, explica el error brevemente.
    """
    agent: Agent

    async def create_agent(self, OpenAiClient: OpenAIChatClient, database_squema: str):
        self.agent = Agent(
            client=OpenAiClient,
            name=self.name,
            instructions=self.instructions + f"\n\nEsquema de la base de datos: {database_squema}",
            tools=[sql_query],
        )

    async def run_agent(self, prompt: str):
        complete_response = await self.agent.run(prompt)
        return complete_response.text