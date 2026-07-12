# services/database_service.py
from sqlalchemy import text

from core.database import engine


class AgentDatabaseService:
    def execute_read_only_query(self, sql_query: str) -> list[dict]:
        """
        Recibe el SQL del agente, solicita una conexión al pool y ejecuta la consulta.
        """
        try:
            with engine.connect() as connection:
                result = connection.execute(text(sql_query))
                rows = [dict(row) for row in result.mappings()]
                return rows
        except Exception as e:
            return [{"error": f"Fallo al ejecutar SQL: {str(e)}"}]

    def execute_preview_query(self, sql_query: str, limit: int = 5) -> list[dict]:
        """"
        Recieves the SQL from the agent, requests a connection from the pool, 
        and executes a preview query with a limit.
        """
        try:
            preview_sql = f"SELECT * FROM ({sql_query.strip().rstrip(';')}) AS agent_query LIMIT {limit}"
            with engine.connect() as connection:
                result = connection.execute(text(preview_sql))
                return [dict(row) for row in result.mappings()]
        except Exception as e:
            return [{"error": f"Fallo al ejecutar SQL preview: {str(e)}"}]