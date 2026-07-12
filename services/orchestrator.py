import asyncio
from typing import Any

from AI.agents.query_agent import queryAgent
from AI.agents.ui_agent import UIAgent
from AI.open_ai_client import OpenAiClient
from services.database import AgentDatabaseService
from services.schema import SchemaCacheService


class AgentOrchestratorService:
    def __init__(self):
        self.open_ai_client = OpenAiClient()
        self.query_agent = queryAgent()
        self.ui_agent = UIAgent()
        self.db_service = AgentDatabaseService()
        self.schema_service = SchemaCacheService()

        database_schema = self.schema_service.get_cache()
        asyncio.run(self.query_agent.create_agent(self.open_ai_client, database_schema))
        asyncio.run(self.ui_agent.create_agent(self.open_ai_client, database_schema))

    def processMessage(self, content: str, chatId: str) -> dict[str, str]:
        del chatId
        agent_response = asyncio.run(self.query_agent.run_agent(content))
        return {"agent_reply": agent_response}

    def build_ui_data(self, content: str, preview_limit: int = 5) -> dict[str, Any]:
        plan = asyncio.run(self.ui_agent.run_agent(content))
        preview_rows = self.db_service.execute_preview_query(plan.sql, preview_limit)
        if preview_rows and "error" in preview_rows[0]:
            return {
                "title": plan.title,
                "component": plan.component,
                "summary": plan.summary,
                "sql": plan.sql,
                "columns": [],
                "preview_rows": preview_rows,
                "rows": [],
                "row_count": 0,
            }

        rows = self.db_service.execute_read_only_query(plan.sql)
        if rows and "error" in rows[0]:
            return {
                "title": plan.title,
                "component": plan.component,
                "summary": plan.summary,
                "sql": plan.sql,
                "columns": [],
                "preview_rows": preview_rows,
                "rows": rows,
                "row_count": 0,
            }

        columns = list(rows[0].keys()) if rows else list(preview_rows[0].keys()) if preview_rows else []
        return {
            "title": plan.title,
            "component": plan.component,
            "summary": plan.summary,
            "sql": plan.sql,
            "columns": columns,
            "preview_rows": preview_rows,
            "rows": rows,
            "row_count": len(rows),
        }

    async def process_audio_stream(self, audio_bytes: bytes) -> bytes:
        del audio_bytes
        return b"RESPUESTA ACA"
