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
                "schema": {},
                "table_descriptions": {},
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
                cols.table_name AS "Tabla",
                cols.column_name AS "Columna", 
                cols.data_type AS "Tipo de Dato", 
                cols.is_nullable AS "Permite Nulos",
                descs.description AS "Descripcion Tabla"
            FROM 
                information_schema.columns AS cols
            LEFT JOIN
                public.data_base_descriptions AS descs
                ON descs.data_base_name = cols.table_name
            WHERE 
                cols.table_schema = 'public'
                AND cols.table_name <> 'data_base_descriptions'
            ORDER BY 
                cols.table_name, 
                cols.ordinal_position;
        """
        
        try:
            rows = db_service.execute_read_only_query(sql_query)
            
            if isinstance(rows, list) and not (len(rows) > 0 and "error" in rows[0]):
                formatted_schema = {}
                table_descriptions = {}
                
                for row in rows:
                    t_name = row["Tabla"]
                    if t_name not in formatted_schema:
                        formatted_schema[t_name] = []

                    table_description = row.get("Descripcion Tabla")
                    if table_description:
                        table_descriptions[t_name] = table_description
                        
                    formatted_schema[t_name].append({
                        "name": row["Columna"],
                        "type": row["Tipo de Dato"],
                        "nullable": True if row["Permite Nulos"] == 'YES' else False
                    })
                
                # Sobrescritura atómica del estado
                self.cache["status"] = "success"
                self.cache["schema"] = formatted_schema
                self.cache["table_descriptions"] = table_descriptions
                print("[CRON] Caché actualizada exitosamente.")
            else:
                print(f"[CRON-ERROR] Falló la consulta SQL: {rows}")
                
        except Exception as e:
            print(f"[CRON-ERROR] Excepción crítica en el job: {str(e)}")