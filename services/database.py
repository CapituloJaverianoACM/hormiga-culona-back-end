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