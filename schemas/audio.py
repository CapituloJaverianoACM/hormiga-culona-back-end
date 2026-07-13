from pydantic import BaseModel, Field


class SpeechSynthesisPayload(BaseModel):
    text: str = Field(..., min_length=1, description="Texto a convertir a voz")
