from services.memory_service import AgentMemoryService


def test_memory_service_reuses_session_for_same_scope_and_conversation():
    memory = AgentMemoryService()
    created = []

    def factory(session_id):
        created.append(session_id)
        return {"session_id": session_id}

    first = memory.get_or_create_session("response", "user-1", factory)
    second = memory.get_or_create_session("response", "user-1", factory)

    assert first is second
    assert created == ["response:user-1"]


def test_memory_service_returns_fresh_session_without_conversation_id():
    memory = AgentMemoryService()
    created = []

    def factory(session_id):
        created.append(session_id)
        return {"session_id": session_id}

    first = memory.get_or_create_session("response", "", factory)
    second = memory.get_or_create_session("response", None, factory)

    assert first is not second
    assert created == [None, None]
