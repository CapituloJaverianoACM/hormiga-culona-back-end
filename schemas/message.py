# schemas/message.py
from pydantic import BaseModel, Field

class MessagePayload(BaseModel):
    content: str = Field(..., min_length=1, description="El mensaje de texto para el agente")
    sender_id: str = Field(..., description="Identificador único del remitente")

class MessageResponse(BaseModel):
    agent_reply: str