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


@app.websocket("ws/agent/{clientID}")
async def websocketAgentEndpoint(
    websocket: WebSocket,
    clientID: str,
    orchestrator: AgentOrchestratorService = Depends() 
):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_bytes()
