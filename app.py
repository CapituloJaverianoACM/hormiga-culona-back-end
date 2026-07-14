from contextlib import asynccontextmanager
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from starlette.requests import HTTPConnection, Request

from schemas.audio import SpeechSynthesisPayload
from schemas.database import QueryPayload
from schemas.message import MessagePayload
from schemas.ui import UIRequestPayload
from services.database import AgentDatabaseService
from services.orchestrator import AgentOrchestratorService
from services.schema import SchemaCacheService


router = APIRouter()


def get_orchestrator_service(connection: HTTPConnection) -> AgentOrchestratorService:
    orchestrator = getattr(connection.app.state, "orchestrator_service", None)
    assert orchestrator is not None
    return orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    schema_service = SchemaCacheService()
    schema_service.refresh_schema_sync()

    orchestrator_service = AgentOrchestratorService()
    await orchestrator_service.initialize()

    app.state.schema_service = schema_service
    app.state.orchestrator_service = orchestrator_service

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        schema_service.refresh_schema_sync,
        trigger="interval",
        hours=1,
        id="update_db_schema_job",
        replace_existing=True,
    )
    scheduler.start()
    print("[INFO] Planificador CRON iniciado correctamente.")

    try:
        yield
    finally:
        scheduler.shutdown()
        print("[INFO] Planificador CRON detenido.")


@router.get("/ping")
def health_monitor():
    return {"status": "ok", "message": "pong"}


@router.post("/agent/chat")
def chat(
    payload: MessagePayload,
    orchestrator: AgentOrchestratorService = Depends(get_orchestrator_service),
):
    return orchestrator.processMessage(
        content=payload.content,
        chatId=payload.sender_id,
    )


@router.post("/agent/sql")
def execute_agent_sql(
    payload: QueryPayload,
    db_service: AgentDatabaseService = Depends(),
):
    result = db_service.execute_read_only_query(payload.sql_query)
    if result and isinstance(result[0], dict) and "error" in result[0]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result[0]["error"],
        )

    return {"status": "success", "data": result}


@router.get("/agent/description")
def get_database_schema(request: Request):
    return request.app.state.schema_service.get_cache()


@router.post("/agent/ui")
def build_agent_ui(
    payload: UIRequestPayload,
    orchestrator: AgentOrchestratorService = Depends(get_orchestrator_service),
):
    return orchestrator.build_ui_data(payload.content, payload.preview_limit)


@router.post("/agent/audio/synthesis")
def synthesize_audio(
    payload: SpeechSynthesisPayload,
    orchestrator: AgentOrchestratorService = Depends(get_orchestrator_service),
):
    audio_bytes = orchestrator.synthesize_audio(payload.text)
    return Response(content=audio_bytes, media_type="audio/wav")


@router.post("/agent/audio/transcription")
async def transcribe_audio(
    file: UploadFile = File(...),
    orchestrator: AgentOrchestratorService = Depends(get_orchestrator_service),
):
    audio_bytes = await file.read()
    return {
        "text": orchestrator.transcribe_audio(
            audio_bytes,
            file.filename or "audio.wav",
            file.content_type or "audio/wav",
        ),
        "filename": file.filename,
        "content_type": file.content_type,
    }


@router.websocket("/ws/agent/voice/{session_id}")
async def direct_voice_agent(
    websocket: WebSocket,
    session_id: str,
    agent: AgentOrchestratorService = Depends(get_orchestrator_service),
):
    await websocket.accept()
    print(f"Sesión de voz {session_id} iniciada.")

    mode = str(websocket.query_params.get("mode") or "response").strip().lower()
    if mode not in {"response", "ui"}:
        mode = "response"

    output_mode = str(websocket.query_params.get("output") or "both").strip().lower()
    if output_mode not in {"audio", "json", "both"}:
        output_mode = "both"

    try:
        preview_limit = int(websocket.query_params.get("preview_limit", "5"))
    except ValueError:
        preview_limit = 5
    preview_limit = max(1, min(preview_limit, 20))

    while True:
        try:
            message = await websocket.receive()
        except (WebSocketDisconnect, RuntimeError):
            print(f"Sesión de voz {session_id} finalizada.")
            break

        if message.get("type") == "websocket.disconnect":
            print(f"Sesión de voz {session_id} finalizada.")
            break

        user_text = (message.get("text") or "").strip()
        user_audio_bytes = message.get("bytes")

        if not user_text and user_audio_bytes is None:
            continue

        try:
            if user_audio_bytes is not None:
                result = await agent.process_audio_request(
                    user_audio_bytes,
                    mode=mode,
                    preview_limit=preview_limit,
                    chat_id=session_id,
                )
            else:
                result = await agent.process_text_request(
                    user_text,
                    chat_id=session_id,
                    mode=mode,
                    preview_limit=preview_limit,
                )

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
            agent_audio_bytes = None
            if output_mode in {"audio", "both"}:
                agent_audio_bytes = agent.synthesize_audio(result["voice_reply"])
        except Exception as exc:
            voice_reply = "No pude procesar la solicitud."
            error_text = f"{voice_reply} {exc}".strip()
            response_payload = {
                "type": "agent_result",
                "mode": mode,
                "user_text": user_text,
                "voice_reply": voice_reply,
                "explanation": error_text,
                "data": {
                    "summary": "Ocurrió un error.",
                    "explanation": error_text,
                    "voice_reply": voice_reply,
                    "preview_rows": [],
                    "columns": [],
                    "row_count": 0,
                },
            }
            agent_audio_bytes = None
            if output_mode in {"audio", "both"}:
                agent_audio_bytes = agent.synthesize_audio(voice_reply)

        try:
            safe_payload = jsonable_encoder(response_payload)
            if output_mode in {"json", "both"}:
                await websocket.send_text(json.dumps(safe_payload, ensure_ascii=False))
            if output_mode in {"audio", "both"} and agent_audio_bytes is not None:
                await websocket.send_bytes(agent_audio_bytes)
        except (WebSocketDisconnect, RuntimeError):
            print(f"Sesión de voz {session_id} finalizada.")
            break


def create_app() -> FastAPI:
    api = FastAPI(
        title="Hormiga Culona APIII",
        description="Backend para el empalme entre el front y el agente",
        version="1.0.0",
        lifespan=lifespan,
    )
    api.include_router(router)
    return api


app = create_app()
