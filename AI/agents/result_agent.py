from agent_framework import Agent
from agent_framework_openai import OpenAIChatClient

from AI.agents.base_agent import BaseAgent
from schemas.ui import ResultNarration


class ResultAgent(BaseAgent):
    name = "Result Agent"
    instructions = """
    Eres un asistente que resume resultados de consultas para dos canales a la vez.
    Responde SIEMPRE con JSON válido que cumpla el schema.

    Reglas:
    - summary: una sola oración corta, máximo 18 palabras.
    - voice_reply: 1 o 2 oraciones cortas, máximo 35 palabras total.
    - explanation: explicación útil en español, breve, natural y enfocada en lo importante.
    - explanation debe interpretar el resultado; no digas solo cuántas tablas o consultas se hicieron.
    - Si hay filas, menciona hallazgos o patrón principal usando solo una muestra pequeña.
    - No enumeres toda la base de datos ni pegues filas completas.
    - No incluyas SQL salvo que ayude a explicar un error.
    - Si no hay datos, dilo claro.
    - Si hubo error, explícalo breve y sin inventar solución.
    """
    agent: Agent

    async def create_agent(self, OpenAiClient: OpenAIChatClient, database_schema: str):
        self.agent = Agent(
            client=OpenAiClient,
            name=self.name,
            instructions=self.instructions + f"\n\nEsquema de la base de datos: {database_schema}",
        )

    async def run_agent(self, prompt: str) -> ResultNarration:
        response = await self.agent.run(prompt, options={"response_format": ResultNarration})
        if response.value:
            return response.value
        raise ValueError(f"No se pudo parsear la narración del resultado: {response.text}")


if __name__ == "__main__":
    assert ResultNarration(summary="ok", explanation="detalle", voice_reply="breve").voice_reply == "breve"
    print("result_agent ok")
