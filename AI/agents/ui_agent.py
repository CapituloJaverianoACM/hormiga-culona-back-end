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
    - Si una métrica numérica ya es numérica pero puede venir nula, usa COALESCE(columna, 0) antes de SUM, AVG u otras agregaciones para evitar totales nulos.
    - Para reportes graficables, devuelve una dimensión categórica o temporal y una métrica numérica agregada.
    - Si el usuario pide top, ranking, "con más", "con menos" o similares, ordena por la métrica agregada y limita el resultado a un tamaño útil para frontend, normalmente 10.
    - Si el usuario menciona explícitamente año y periodo, cada periodo y cada año, o un cálculo acumulado sobre cortes semestrales, primero agrega al grano base correcto en una subconsulta o CTE. En egresos e ingresos ese grano suele ser categoria + anio + periodo. Luego haz la suma final sobre ese resultado intermedio.
    - Cuando agrupes por categorías de texto, excluye nulos y textos vacíos si eso evita categorías basura.
    - No inventes columnas derivadas que no existan; si necesitas renombrar, usa alias claros.

    Prioridades para SQL correcto:
    - Si la solicitud habla de presupuesto total por rubro a través de varios periodos o años, no agregues solo por rubro directamente: agrega primero por rubro, anio y periodo, y después vuelve a sumar.
    - Evita consultas que dejen la métrica principal en null si se puede resolver con COALESCE.
    - Si el usuario pide gráfico, prioriza una consulta fácil de renderizar: una columna etiqueta y una columna numérica.

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
        response = await self.agent.run(self.inject_prompt(prompt), options={"response_format": UIPlan})
        if response.value:
            return response.value
        raise ValueError(f"No se pudo parsear el plan UI: {response.text}")


if __name__ == "__main__":
    assert UIPlan(title="Ventas", component="table", sql="SELECT 1", summary="ok").component == "table"
    print("ui_agent ok")
