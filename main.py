# Here goes fastapi ports and init
from fastapi import FastAPI, Depends ,WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Importar los eschemas
from schemas.message import MessagePayload, MessageResponse

# Importar los servicios
from services.orchestrator import AgentOrchestratorService

app = FastAPI(
    title="Hormiga Culona APIII",
    description="Backend para el empalme entre el front y el agente",
    version="1.0.0"
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
