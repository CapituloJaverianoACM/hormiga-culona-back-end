from AI.agents.tools.sql_query import sql_query

def testsql():
    sql_query_result = sql_query("SELECT * FROM egresos LIMIT 1;")

    print("Resultado de la consulta SQL:", sql_query_result)

if __name__ == "__main__":
    testsql()