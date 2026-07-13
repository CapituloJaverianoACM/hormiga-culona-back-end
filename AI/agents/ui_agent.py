from agent_framework import Agent
from agent_framework_openai import OpenAIChatClient

from AI.agents.base_agent import BaseAgent
from schemas.ui import UIPlan


class UIAgent(BaseAgent):
    """"
    UIAgent is an agent that translates user requests into frontend query plans to 
    display data in a user interface. It generates SQL queries and provides metadata for rendering the results."""
    name = "UI Agent"
    instructions = """
    Eres un asistente que traduce solicitudes del usuario a planes de consulta para frontend.
    Responde SIEMPRE con un JSON válido que cumpla el schema.
    Reglas:
    - Genera una sola consulta SQL de lectura.
    - Usa únicamente tablas y columnas del esquema entregado.
    - component debe ser uno de: table, bar_chart, line_chart, card, list.
    - title debe ser corto y claro.
    - summary debe ser UNA sola oración corta, máximo 18 palabras.
    - summary solo describe qué verá el frontend; no incluyas resultados, números, recomendaciones, SQL, análisis ni contexto extra.
    - Si una métrica monetaria viene como texto, antes de convertirla usa este patrón:
      NULLIF(regexp_replace(columna_texto, '[^0-9.-]', '', 'g'), '')::numeric
    - Para reportes graficables, devuelve una dimensión categórica o temporal y una métrica numérica agregada.

    Reglas de accesibilidad y estilo:
    - Escribe títulos y summary en español claro y fácil de entender.
    - No uses notación matemática, LaTeX, fórmulas ni símbolos especiales.
    - No uses abreviaturas raras ni jerga técnica innecesaria.
    - Si el pedido del usuario es ambiguo, elige la opción más simple y útil con el esquema disponible.
    - Si falta contexto de negocio o de bases de datos disponibles, no lo inventes.
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
