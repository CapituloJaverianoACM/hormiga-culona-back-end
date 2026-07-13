from scripts.database_schema import sql_schema

def test_sql_schema():
    # Call the function to get the SQL schema
    schema = sql_schema()
    print("Database Schema:", schema)

if __name__ == "__main__":
    test_sql_schema()