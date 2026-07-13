from collections.abc import Callable
from typing import Any


class AgentMemoryService:

    def __init__(self):
        self._sessions: dict[str, Any] = {}

    def get_or_create_session(
        self,
        scope: str,
        conversation_id: str | None,
        factory: Callable[[str | None], Any],
    ) -> Any:
        clean_id = (conversation_id or "").strip()
        if not clean_id:
            return factory(None)

        key = self._key(scope, clean_id)
        session = self._sessions.get(key)
        if session is None:
            session = factory(key)
            self._sessions[key] = session
        return session

    def save_session(self, scope: str, conversation_id: str | None, session: Any) -> None:
        clean_id = (conversation_id or "").strip()
        if not clean_id:
            return
        self._sessions[self._key(scope, clean_id)] = session

    def _key(self, scope: str, conversation_id: str) -> str:
        return f"{scope}:{conversation_id}"
