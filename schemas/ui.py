from typing import Literal

from pydantic import BaseModel, Field


class UIRequestPayload(BaseModel):
    content: str = Field(..., min_length=1, description="Solicitud del usuario para construir la data del frontend")
    preview_limit: int = Field(5, ge=1, le=20, description="Cantidad de filas de muestra para validar la consulta")


class UIPlan(BaseModel):
    title: str = Field(..., description="Título sugerido para el bloque UI")
    component: Literal["table", "bar_chart", "line_chart", "card", "list"] = Field(
        ..., description="Tipo de componente recomendado"
    )
    sql: str = Field(..., description="Consulta SQL de solo lectura")
    summary: str | None = Field(None, description="Resumen breve de lo que devuelve la consulta")


class ResultNarration(BaseModel):
    summary: str | None = Field(None, description="Resumen muy corto del resultado")
    explanation: str = Field(..., description="Explicación breve pero útil para UI/API")
    voice_reply: str = Field(..., description="Respuesta corta pensada para audio")


class UIDataResponse(BaseModel):
    title: str
    component: str
    summary: str | None = None
    explanation: str | None = None
    voice_reply: str | None = None
    sql: str
    columns: list[str]
    preview_rows: list[dict]
    rows: list[dict]
    row_count: int
