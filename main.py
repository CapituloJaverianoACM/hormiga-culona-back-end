from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends ,WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Importar los eschemas
from schemas.message import MessagePayload
from schemas.database import QueryPayload

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

    # 1. Extraemos la cadena SQL del body validado
    query_string = payload.sql_query
    
    # 2. Delegamos la ejecución transaccional al servicio de base de datos
    resultado = db_service.execute_read_only_query(query_string)
    
    # 3. Retornamos la respuesta serializada al agente
    return {
        "status": "success",
        "data": resultado
    }

@app.get("/agent/description")
def get_database_schema():
    return schema_service.get_cache()

@app.websocket("/ws/agent/voice/{session_id}")
async def direct_voice_agent(
    websocket: WebSocket,
    session_id: str,
    agent: AgentOrchestratorService = Depends() 
):

    await websocket.accept()
    print(f"Sesión de voz {session_id} iniciada.")
    
    try:
        while True:
            user_audio_bytes = await websocket.receive_bytes()
            
            agent_audio_bytes = await agent.process_audio_stream(user_audio_bytes)
            
            # Transmisión: Enviamos los bytes de voz del agente de vuelta al cliente
            await websocket.send_bytes(agent_audio_bytes)
            
    except WebSocketDisconnect:
        print(f"Sesión de voz {session_id} finalizada.")



