import asyncio

from services.response_service import AgentResponseService


class _StubQueryAgent:
    def __init__(self):
        self.calls = []

    async def run_agent(self, prompt: str, session=None):
        self.calls.append((prompt, session))
        return "respuesta"


def test_response_service_passes_session_to_query_agent():
    query_agent = _StubQueryAgent()
    service = AgentResponseService(query_agent)
    session = object()

    result = asyncio.run(service.build_response_data("hola", session=session))

    assert query_agent.calls == [("hola", session)]
    assert result["agent_reply"] == "respuesta"
    assert result["voice_reply"] == "respuesta"
