import asyncio
from types import SimpleNamespace

import AI.agents.query_agent as query_agent_module


class _FakeAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.runs: list[tuple[str, object]] = []

    async def run(self, prompt: str, session=None):
        self.runs.append((prompt, session))
        return SimpleNamespace(text="respuesta simulada")


def test_query_agent_create_and_run_without_live_services(monkeypatch):
    created: dict[str, _FakeAgent] = {}

    def fake_agent_factory(**kwargs):
        agent = _FakeAgent(**kwargs)
        created["agent"] = agent
        return agent

    def fake_history_provider(name: str, load_messages: bool = True):
        return {"name": name, "load_messages": load_messages}

    monkeypatch.setattr(query_agent_module, "Agent", fake_agent_factory)
    monkeypatch.setattr(query_agent_module, "InMemoryHistoryProvider", fake_history_provider)

    query_agent = query_agent_module.queryAgent()
    client = object()
    schema = {"tables": ["ingresos", "egresos"]}

    async def _run():
        await query_agent.create_agent(client, schema)
        response = await query_agent.run_agent("hola", session="session-1")
        assert response == "respuesta simulada"

    asyncio.run(_run())

    fake_agent = created["agent"]
    assert fake_agent.kwargs["client"] is client
    assert fake_agent.kwargs["name"] == query_agent.name
    assert fake_agent.kwargs["tools"] == [query_agent_module.sql_query]
    assert fake_agent.kwargs["context_providers"] == [{"name": "chat_history", "load_messages": True}]
    assert "ingresos" in fake_agent.kwargs["instructions"]
    assert fake_agent.runs == [(
        "Solicitud del usuario:\nhola\n\nResponde usando esta solicitud como la tarea principal.",
        "session-1",
    )]
