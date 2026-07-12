from agent_framework import Agent
from agent_framework_openai import OpenAIChatClient

from AI.agents.base_agent import BaseAgent
from schemas.ui import UIPlan


class UIAgent(BaseAgent):
    name = "UI Agent"
    instructions = """
    Eres un asistente que traduce solicitudes del usuario a planes de consulta para frontend.
    Responde SIEMPRE con un JSON válido que cumpla el schema.
    Reglas:
    - Genera una sola consulta SQL de lectura.
    - Usa únicamente tablas y columnas del esquema entregado.
    - Prefiere consultas simples para un hackathon.
    - component debe ser uno de: table, bar_chart, line_chart, card, list.
    - title debe ser corto y claro.
    - summary debe describir qué verá el frontend.
    - Si una métrica monetaria viene como texto, antes de convertirla usa este patrón:
      NULLIF(regexp_replace(columna_texto, '[^0-9.-]', '', 'g'), '')::numeric
    - Para reportes graficables, devuelve una dimensión categórica o temporal y una métrica numérica agregada.
    """
    agent: Agent

    async def create_agent(self, OpenAiClient: OpenAIChatClient, database_schema: str):
        self.agent = Agent(
            client=OpenAiClient,
            name=self.name,
            instructions=self.instructions + f"\n\nEsquema de la base de datos: {database_schema}",
        )

    async def run_agent(self, prompt: str) -> UIPlan:
        response = await self.agent.run(prompt, options={"response_format": UIPlan})
        if response.value:
            return response.value
        raise ValueError(f"No se pudo parsear el plan UI: {response.text}")


if __name__ == "__main__":
    assert UIPlan(title="Ventas", component="table", sql="SELECT 1", summary="ok").component == "table"
    print("ui_agent ok")
