# services/schema_cache_service.py
from services.database import AgentDatabaseService

class SchemaCacheService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchemaCacheService, cls).__new__(cls)
            # Estado inicial de la memoria RAM
            cls._instance.cache = {
                "status": "initializing",
                "database_name": "Base de datos abierta",
                "schema": {}
            }
        return cls._instance

    def get_cache(self) -> dict:
        return self.cache

    def refresh_schema_sync(self):
        """
        Esta es la tarea atómica que ejecutará el Cron Job.
        Extrae la metadata y actualiza el diccionario en memoria.
        """
        print("[CRON] Iniciando actualización de caché del esquema...")
        db_service = AgentDatabaseService()
        
        sql_query = """
            SELECT 
                table_name AS "Tabla",
                column_name AS "Columna", 
                data_type AS "Tipo de Dato", 
                is_nullable AS "Permite Nulos"
            FROM 
                information_schema.columns
            WHERE 
                table_schema = 'public'
            ORDER BY 
                table_name, 
                ordinal_position;
        """
        
        try:
            rows = db_service.execute_read_only_query(sql_query)
            
            if isinstance(rows, list) and not (len(rows) > 0 and "error" in rows[0]):
                formatted_schema = {}
                
                for row in rows:
                    t_name = row["Tabla"]
                    if t_name not in formatted_schema:
                        formatted_schema[t_name] = []
                        
                    formatted_schema[t_name].append({
                        "name": row["Columna"],
                        "type": row["Tipo de Dato"],
                        "nullable": True if row["Permite Nulos"] == 'YES' else False
                    })
                
                # Sobrescritura atómica del estado
                self.cache["status"] = "success"
                self.cache["schema"] = formatted_schema
                print("[CRON] Caché actualizada exitosamente.")
            else:
                print(f"[CRON-ERROR] Falló la consulta SQL: {rows}")
                
        except Exception as e:
            print(f"[CRON-ERROR] Excepción crítica en el job: {str(e)}")