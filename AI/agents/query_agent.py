from agent_framework import Agent
from agent_framework_openai import OpenAIChatClient 
from AI.agents.base_agent import BaseAgent
from AI.agents.tools.sql_query import sql_query

class queryAgent(BaseAgent):
    name = "Query Agent"
    instructions = """
    Eres un asistente de IA que crea Querys SQL basadas en las preguntas generadas por el usuario.
    Usa la tool sql_query para ejecutar las consultas SQL y obtener los resultados de la base de datos.
    """
    agent: Agent
    async def create_agent(self, OpenAiClient: OpenAIChatClient, database_squema: str):
        self.instructions = self.instructions + f"\n\nEsquema de la base de datos: {database_squema}"
        self.agent = Agent(
            client=OpenAiClient,
            name=self.name,
            instructions=self.instructions,
            tools=[sql_query]
        )

    async def run_agent(self, prompt: str):
        complete_response = await self.agent.run(prompt)
        response = complete_response.text
        return response