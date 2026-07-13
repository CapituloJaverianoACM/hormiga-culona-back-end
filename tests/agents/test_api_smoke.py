from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

import main
from schemas.ui import UIRequestPayload
from services.database import AgentDatabaseService
from services.orchestrator import AgentOrchestratorService


@asynccontextmanager
async def _no_lifespan(_app):
    yield


class _StubDatabaseService:
    def __init__(self):
        self.queries: list[str] = []

    def execute_read_only_query(self, sql_query: str) -> list[dict]:
        self.queries.append(sql_query)
        return [{"ok": 1}]


class _StubOrchestrator:
    def __init__(self):
        self.calls: list[tuple[str, int]] = []

    def build_ui_data(self, content: str, preview_limit: int = 5) -> dict:
        self.calls.append((content, preview_limit))
        return {
            "title": "Demo",
            "component": "table",
            "summary": "ok",
            "explanation": "ok",
            "voice_reply": "ok",
            "sql": "SELECT 1",
            "columns": ["ok"],
            "preview_rows": [{"ok": 1}],
            "rows": [{"ok": 1}],
            "row_count": 1,
        }


def _client_with_overrides(*, db_service=None, orchestrator=None) -> TestClient:
    main.app.router.lifespan_context = _no_lifespan
    main.app.dependency_overrides.clear()
    if db_service is not None:
        main.app.dependency_overrides[AgentDatabaseService] = lambda: db_service
    if orchestrator is not None:
        main.app.dependency_overrides[AgentOrchestratorService] = lambda: orchestrator
    return TestClient(main.app)


def test_sql_endpoint_rejects_empty_query_with_http_error():
    client = _client_with_overrides(db_service=_StubDatabaseService())

    response = client.post("/agent/sql", json={"sql_query": ""})

    assert response.status_code == 422


def test_sql_endpoint_rejects_non_read_only_query_with_http_error():
    client = _client_with_overrides()

    response = client.post("/agent/sql", json={"sql_query": "DELETE FROM egresos"})

    assert response.status_code == 400


def test_ui_request_payload_no_longer_requires_sender_id():
    payload = UIRequestPayload.model_validate({
        "content": "Muéstrame gastos",
        "preview_limit": 3,
    })

    assert payload.content == "Muéstrame gastos"
    assert payload.preview_limit == 3


def test_ui_endpoint_accepts_requests_without_sender_id():
    orchestrator = _StubOrchestrator()
    client = _client_with_overrides(orchestrator=orchestrator)

    response = client.post(
        "/agent/ui",
        json={
            "content": "Muéstrame gastos",
            "preview_limit": 3,
        },
    )

    assert response.status_code == 200
    assert response.json()["sql"] == "SELECT 1"
    assert orchestrator.calls == [("Muéstrame gastos", 3)]
