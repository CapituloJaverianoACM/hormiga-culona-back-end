from typing import Any


class AgentResponseService:
    def __init__(self, query_agent):
        self.query_agent = query_agent

    async def build_response_data(self, content: str, session: Any = None) -> dict[str, Any]:
        explanation = (await self.query_agent.run_agent((content or "").strip(), session=session)).strip()
        return {
            "agent_reply": explanation,
            "summary": explanation,
            "explanation": explanation,
            "voice_reply": explanation,
            "sql": "",
            "columns": [],
            "preview_rows": [],
            "row_count": 0,
        }
