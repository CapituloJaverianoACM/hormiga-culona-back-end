from pydantic import BaseModel, Field


class QueryPayload(BaseModel):
    sql_query: str = Field(..., description="Consulta SQL cruda a ejecutar en Supabase")


class SQLPreviewPayload(BaseModel):
    sql_query: str = Field(..., description="Consulta SQL cruda a ejecutar en Supabase")
    limit: int = Field(5, ge=1, le=20, description="Cantidad de filas a retornar en la vista previa")