# services/database_service.py
import re

from fastapi import HTTPException
from sqlalchemy import text

from core.database import engine


class SQLValidationError(ValueError):
    pass


class AgentDatabaseService:
    _READ_ONLY_START = re.compile(r"^(select|with)\b", re.IGNORECASE)
    _BLOCKED_TOKENS = re.compile(
        r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|comment|merge|call|execute|exec|copy|vacuum|analyze|refresh|set|reset|show|use|attach|detach)\b",
        re.IGNORECASE,
    )

    def execute_read_only_query(self, sql_query: str) -> list[dict]:
        """
        Recibe el SQL del agente, valida que sea de solo lectura y ejecuta la consulta.
        """
        try:
            normalized_sql = self._validate_read_only_sql(sql_query)
            with engine.connect() as connection:
                result = connection.execute(text(normalized_sql))
                return [dict(row) for row in result.mappings()]
        except SQLValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Fallo al ejecutar SQL: {str(exc)}") from exc

    def execute_preview_query(self, sql_query: str, limit: int = 5) -> list[dict]:
        """"
        Recieves the SQL from the agent, requests a connection from the pool,
        and executes a preview query with a limit.
        """
        try:
            normalized_sql = self._validate_read_only_sql(sql_query)
            preview_sql = f"SELECT * FROM ({normalized_sql.rstrip(';')}) AS agent_query LIMIT {limit}"
            with engine.connect() as connection:
                result = connection.execute(text(preview_sql))
                return [dict(row) for row in result.mappings()]
        except SQLValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Fallo al ejecutar SQL preview: {str(exc)}") from exc

    def _validate_read_only_sql(self, sql_query: str) -> str:
        normalized_sql = self._strip_leading_comments(sql_query or "").strip()
        if not normalized_sql:
            raise SQLValidationError("La consulta SQL está vacía.")
        if ";" in normalized_sql.rstrip(";"):
            raise SQLValidationError("Solo se permite una consulta SQL por petición.")
        if not self._READ_ONLY_START.match(normalized_sql):
            raise SQLValidationError("Solo se permiten consultas SQL de solo lectura (SELECT/WITH).")
        sql_without_strings = re.sub(r"'[^']*'|\"[^\"]*\"", "", normalized_sql)
        if self._BLOCKED_TOKENS.search(sql_without_strings):
            raise SQLValidationError("La consulta contiene instrucciones no permitidas para modo de solo lectura.")
        return normalized_sql

    def _strip_leading_comments(self, sql_query: str) -> str:
        cleaned = sql_query.lstrip()
        while True:
            if cleaned.startswith("--"):
                newline_index = cleaned.find("\n")
                cleaned = "" if newline_index == -1 else cleaned[newline_index + 1 :].lstrip()
                continue
            if cleaned.startswith("/*"):
                end_index = cleaned.find("*/")
                if end_index == -1:
                    raise SQLValidationError("Comentario SQL sin cerrar.")
                cleaned = cleaned[end_index + 2 :].lstrip()
                continue
            return cleaned