from pydantic import BaseModel, Field

class QueryPayload(BaseModel):
    sql_query: str = Field(..., description="Consulta SQL cruda a ejecutar en Supabase")