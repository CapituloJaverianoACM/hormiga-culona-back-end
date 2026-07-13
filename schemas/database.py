from pydantic import BaseModel, Field, field_validator


class QueryPayload(BaseModel):
    sql_query: str = Field(..., description="Consulta SQL cruda a ejecutar en Supabase")

    @field_validator("sql_query")
    @classmethod
    def validate_sql_not_empty(cls, value: str) -> str:
        sql = value.strip()
        if not sql:
            raise ValueError("sql_query no puede estar vacío")
        return sql


class SQLPreviewPayload(BaseModel):
    sql_query: str = Field(..., description="Consulta SQL cruda a ejecutar en Supabase")
    limit: int = Field(5, ge=1, le=20, description="Cantidad de filas a retornar en la vista previa")