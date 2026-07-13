import asyncio
from typing import Any

from AI.agents.query_agent import queryAgent
from AI.agents.result_agent import ResultAgent
from AI.agents.ui_agent import UIAgent
from AI.audio_client import AzureSpeechSynthesisClient, AzureTranscriptionClient
from AI.open_ai_client import OpenAiClient
from services.audio_service import AgentAudioService
from services.database import AgentDatabaseService
from services.memory_service import AgentMemoryService
from services.response_service import AgentResponseService
from services.schema import SchemaCacheService
from services.ui_service import AgentUIService


class AgentOrchestratorService:
    """Router ligero entre response, ui y audio."""

    def __init__(self):
        self.open_ai_client = OpenAiClient()
        self.query_agent = queryAgent()
        self.ui_agent = UIAgent()
        self.result_agent = ResultAgent()
        self.db_service = AgentDatabaseService()
        self.schema_service = SchemaCacheService()
        self.audio_service = AgentAudioService(AzureTranscriptionClient(), AzureSpeechSynthesisClient())
        self.memory_service = AgentMemoryService()
        self.response_service = AgentResponseService(self.query_agent)
        self.ui_service = AgentUIService(self.ui_agent, self.result_agent, self.db_service)

    async def initialize(self) -> None:
        database_schema = self.schema_service.get_cache()
        await self.query_agent.create_agent(self.open_ai_client, database_schema)
        await self.ui_agent.create_agent(self.open_ai_client, database_schema)
        await self.result_agent.create_agent(self.open_ai_client, database_schema)

    async def process_text_request(
        self,
        content: str,
        chat_id: str,
        mode: str = "response",
        preview_limit: int = 5,
    ) -> dict[str, Any]:
        mode = (mode or "response").strip().lower()

        if mode == "ui":
            result_data = await self._build_ui_data_async(content, preview_limit)
            return {
                "mode": "ui",
                "user_text": content,
                "data": result_data,
                "reply_text": result_data["voice_reply"],
                "explanation": result_data["explanation"],
                "voice_reply": result_data["voice_reply"],
            }

        response_data = await self._build_response_data_async(content, chat_id)
        return {
            "mode": "response",
            "user_text": content,
            "data": response_data,
            "reply_text": response_data["voice_reply"],
            "explanation": response_data["explanation"],
            "voice_reply": response_data["voice_reply"],
        }

    def processMessage(self, content: str, chatId: str) -> dict[str, Any]:
        result = asyncio.run(self.process_text_request(content, chatId, mode="response"))
        return result["data"]

    def build_ui_data(self, content: str, preview_limit: int = 5) -> dict[str, Any]:
        result = asyncio.run(self.process_text_request(content, "ui", mode="ui", preview_limit=preview_limit))
        return result["data"]

    async def _build_response_data_async(self, content: str, chat_id: str | None) -> dict[str, Any]:
        session = self.memory_service.get_or_create_session(
            "response",
            chat_id,
            lambda session_id: self.query_agent.agent.create_session(session_id=session_id),
        )
        response = await self.response_service.build_response_data(content, session=session)
        self.memory_service.save_session("response", chat_id, session)
        return response

    async def _build_ui_data_async(self, content: str, preview_limit: int = 5) -> dict[str, Any]:
        return await self.ui_service.build_ui_data(content, preview_limit)

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", content_type: str = "audio/wav") -> str:
        return self.audio_service.transcribe_audio(audio_bytes, filename, content_type)

    def synthesize_audio(self, text: str) -> bytes:
        return self.audio_service.synthesize_audio(text)

    async def process_audio_request(
        self,
        audio_bytes: bytes,
        mode: str = "response",
        preview_limit: int = 5,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
        chat_id: str = "voice",
    ) -> dict[str, Any]:
        user_text = self.transcribe_audio(audio_bytes, filename, content_type)
        result = await self.process_text_request(user_text, chat_id, mode=mode, preview_limit=preview_limit)
        return {
            "mode": result["mode"],
            "user_text": user_text,
            "data": result["data"],
            "reply_text": result["reply_text"],
            "explanation": result["explanation"],
            "voice_reply": result["voice_reply"],
        }

    async def process_audio_stream(self, audio_bytes: bytes, mode: str = "response", preview_limit: int = 5) -> tuple[dict[str, Any], bytes]:
        result = await self.process_audio_request(audio_bytes, mode=mode, preview_limit=preview_limit)
        response_payload = {
            "type": "agent_result",
            "mode": result["mode"],
            "user_text": result["user_text"],
            "voice_reply": result["voice_reply"],
            "explanation": result["explanation"],
            "data": result["data"],
        }
        if response_payload["mode"] != "ui" and isinstance(response_payload["data"], dict):
            response_payload["data"].pop("rows", None)
        return response_payload, self.synthesize_audio(result["voice_reply"])
