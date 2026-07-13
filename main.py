from contextlib import asynccontextmanager

import json

from fastapi import FastAPI, Depends, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response

# Importar los eschemas
from schemas.audio import SpeechSynthesisPayload
from schemas.message import MessagePayload
from schemas.database import QueryPayload, SQLPreviewPayload
from schemas.ui import UIRequestPayload

# Importar los servicios
from services.orchestrator import AgentOrchestratorService
from services.database import AgentDatabaseService
from services.schema import SchemaCacheService

from apscheduler.schedulers.asyncio import AsyncIOScheduler

schema_service = SchemaCacheService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """ Gestor del ciclo de vida del servidor (Startup / Shutdown) """
    
    # 1. Ejecutamos la carga inicial inmediatamente antes de recibir tráfico
    schema_service.refresh_schema_sync()
    
    # 2. Configuramos y arrancamos el Cron Job
    scheduler = AsyncIOScheduler()
    
    # Programamos la tarea para que corra cada 1 hora (3600 segundos) exactos
    scheduler.add_job(
        schema_service.refresh_schema_sync, 
        trigger='interval', 
        hours=1,
        id='update_db_schema_job',
        replace_existing=True
    )
    scheduler.start()
    print("[INFO] Planificador CRON iniciado correctamente.")
    
    yield # Aquí FastAPI comienza a aceptar peticiones HTTP
    
    scheduler.shutdown()
    print("[INFO] Planificador CRON detenido.")

app = FastAPI(
    title="Hormiga Culona APIII",
    description="Backend para el empalme entre el front y el agente",
    version="1.0.0",
    lifespan=lifespan
)

# Despues se añadira el CORS si desplegamos
# app.add_middleware()

@app.get("/ping")
def healthMonitor():
    return {"status" : "ok", "message" : "pong"}


@app.post("/agent/chat")
def chat(
    payload: MessagePayload, 
    orchestrator: AgentOrchestratorService = Depends()
):
    resultado = orchestrator.processMessage(
        content=payload.content, 
        chatId=payload.sender_id
    )
    
    return resultado

@app.post("/agent/sql")
def execute_agent_sql(
    payload: QueryPayload,
    db_service: AgentDatabaseService = Depends()
):
    """
    Endpoint que actúa como herramienta para que el agente ejecute SQL en la base de datos.
    Recibe la consulta validada a través del DTO y retorna los resultados.
    """

    resultado = db_service.execute_read_only_query(payload.sql_query)
    if resultado and isinstance(resultado[0], dict) and "error" in resultado[0]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=resultado[0]["error"],
        )

    return {
        "status": "success",
        "data": resultado
    }

@app.get("/agent/description")
def get_database_schema():
    return schema_service.get_cache()

@app.post("/agent/ui")
def build_agent_ui(
    payload: UIRequestPayload,
    orchestrator: AgentOrchestratorService = Depends()
):
    return orchestrator.build_ui_data(payload.content, payload.preview_limit)


@app.post("/agent/audio/synthesis")
def synthesize_audio(
    payload: SpeechSynthesisPayload,
    orchestrator: AgentOrchestratorService = Depends(),
):
    audio_bytes = orchestrator.synthesize_audio(payload.text)
    return Response(content=audio_bytes, media_type="audio/wav")


@app.post("/agent/audio/transcription")
async def transcribe_audio(
    file: UploadFile = File(...),
    orchestrator: AgentOrchestratorService = Depends(),
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


@app.websocket("/ws/agent/voice/{session_id}")
async def direct_voice_agent(
    websocket: WebSocket,
    session_id: str,
    agent: AgentOrchestratorService = Depends()
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
