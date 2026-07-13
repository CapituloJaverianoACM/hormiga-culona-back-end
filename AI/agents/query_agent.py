from typing import Any

from agent_framework import Agent, InMemoryHistoryProvider
from agent_framework_openai import OpenAIChatClient

from AI.agents.base_agent import BaseAgent
from AI.agents.tools.sql_query import sql_query


class queryAgent(BaseAgent):
    """"
    queryAgent is an agent that answers user questions using SQL queries."""
    name = "Query Agent"
    instructions = """
    Eres un asistente de IA que responde preguntas del usuario usando SQL.
    Usa la tool sql_query para ejecutar consultas de solo lectura cuando haga falta y responde con lenguaje natural.
    No inventes datos. Si la consulta falla, explica el error brevemente.

    Reglas de estilo:
    - Responde corto por defecto: máximo 2 oraciones y máximo 120 palabras.
    - Si el usuario solo saluda o pregunta en qué puedes ayudar, responde breve y sin ejecutar consultas.
    - No des listas largas, ejemplos extensos, manuales, ni descripción detallada del esquema salvo que el usuario lo pida.
    - Escribe en español claro, simple y accesible para público general.
    - No uses notación matemática, LaTeX, símbolos como ≤ ≥ ≈ →, fracciones ni fórmulas.
    - No uses Markdown complejo, tablas, ni bloques de código salvo que el usuario lo pida.
    - Si mencionas números, exprésalos en texto simple y explica qué significan.
    - Si aparece un término técnico o una columna poco clara, explícalo en palabras sencillas.
    - Si falta contexto del negocio o de la base de datos, dilo claramente y no inventes interpretaciones.
    """
    agent: Agent

    async def create_agent(self, OpenAiClient: OpenAIChatClient, database_squema: str):
        self.agent = Agent(
            client=OpenAiClient,
            name=self.name,
            instructions=self.instructions + f"\n\nEsquema de la base de datos: {database_squema}",
            tools=[sql_query],
            context_providers=[InMemoryHistoryProvider("chat_history", load_messages=True)],
        )

    async def run_agent(self, prompt: str, session: Any = None):
        complete_response = await self.agent.run(self.inject_prompt(prompt), session=session)
        return complete_response.text