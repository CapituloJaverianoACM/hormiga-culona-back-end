import argparse
import csv
import os
import dotenv
from pathlib import Path

load_dotenv = dotenv.load_dotenv()

TABLES = {
    "data_base_descriptions": {
        "file": "data_base_descriptions.csv",
        "columns": [
            ("data_base_name", "TEXT PRIMARY KEY"),
            ("description", "TEXT"),
        ],
    },
    "ingresos": {
        "file": "ingresos_consolidado.csv",
        "columns": [
            ("id", "TEXT PRIMARY KEY"),
            ("anio", "INTEGER"),
            ("periodo", "INTEGER"),
            ("descripcion", "TEXT"),
            ("presupuesto_inicial", "DOUBLE PRECISION"),
            ("adiciones", "DOUBLE PRECISION"),
            ("reducciones", "DOUBLE PRECISION"),
            ("creditos", "DOUBLE PRECISION"),
            ("contracreditos", "DOUBLE PRECISION"),
            ("presupuesto_final", "DOUBLE PRECISION"),
            ("recaudos", "DOUBLE PRECISION"),
            ("recaudo_acumulado", "DOUBLE PRECISION"),
            ("saldo_por_recaudar", "DOUBLE PRECISION"),
            ("pct_ejecucion", "DOUBLE PRECISION"),
            ("archivo_origen", "TEXT"),
        ],
    },
    "egresos": {
        "file": "egresos_consolidado.csv",
        "columns": [
            ("id", "TEXT PRIMARY KEY"),
            ("anio", "INTEGER"),
            ("periodo", "INTEGER"),
            ("descripcion_rubro", "TEXT"),
            ("presupuesto_inicial", "DOUBLE PRECISION"),
            ("adiciones", "DOUBLE PRECISION"),
            ("reducciones", "DOUBLE PRECISION"),
            ("creditos", "DOUBLE PRECISION"),
            ("contracreditos", "DOUBLE PRECISION"),
            ("presupuesto_definitivo", "DOUBLE PRECISION"),
            ("disponibilidad_acumulada", "DOUBLE PRECISION"),
            ("compromiso_acumulado", "DOUBLE PRECISION"),
            ("obligaciones", "DOUBLE PRECISION"),
            ("pagos_acumulados", "DOUBLE PRECISION"),
            ("saldo_reservas", "DOUBLE PRECISION"),
            ("pct_ejecucion", "DOUBLE PRECISION"),
            ("archivo_origen", "TEXT"),
        ],
    },
}

NUMERIC_FIELDS = {
    "anio",
    "periodo",
    "presupuesto_inicial",
    "adiciones",
    "reducciones",
    "creditos",
    "contracreditos",
    "presupuesto_final",
    "presupuesto_definitivo",
    "disponibilidad_acumulada",
    "compromiso_acumulado",
    "obligaciones",
    "pagos_acumulados",
    "saldo_reservas",
    "recaudos",
    "recaudo_acumulado",
    "saldo_por_recaudar",
    "pct_ejecucion",
}

TYPE_MAP = {
    "TEXT": "Text",
    "INTEGER": "Integer",
    "DOUBLE PRECISION": "Float",
}


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL_PIPELINE")
    if not database_url:
        raise ValueError("La variable DATABASE_URL_PIPELINE no esta configurada.")
    return database_url


def parse_value(field: str, value: str):
    if value == "":
        return None
    if field == "data_base_name":
        return value
    if field in {"anio", "periodo"}:
        return int(float(value))
    if field in NUMERIC_FIELDS:
        cleaned = value.strip()
        negative = cleaned.startswith("(") and cleaned.endswith(")")
        cleaned = cleaned.strip("()").replace(",", "").replace(" ", "").replace("$", "")
        upper_cleaned = cleaned.upper()
        if upper_cleaned in {"", "-", "+", "-0", "+0", "ERROR:#DIV/0!", "#DIV/0!", "ERROR:#REF!", "#REF!"} or upper_cleaned.startswith("ERROR:"):
            return None
        number = float(cleaned)
        return -number if negative else number
    return value


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: parse_value(key, value) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def verify_inputs(input_dir=".") -> dict[str, int]:
    input_path = Path(input_dir)
    loaded = {}
    for table_name, config in TABLES.items():
        csv_path = input_path / config["file"]
        if not csv_path.exists():
            raise FileNotFoundError(f"No existe {csv_path}")
        rows = read_csv_rows(csv_path)
        loaded[table_name] = len(rows)
        print(f"[VERIFY] {table_name}: {len(rows)} filas listas desde {csv_path}")
    return loaded


def run_load(input_dir=".", verify_only: bool = False) -> dict[str, int]:
    loaded = verify_inputs(input_dir=input_dir)
    get_database_url()
    if verify_only:
        return loaded

    from sqlalchemy import Column, Float, Integer, MetaData, Table, Text, create_engine, text
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.pool import NullPool

    type_map = {"Text": Text, "Integer": Integer, "Float": Float}

    def create_db_engine():
        return create_engine(get_database_url(), pool_pre_ping=True, poolclass=NullPool)

    def ensure_schema(connection, table_name: str, columns: list[tuple[str, str]]) -> None:
        columns_sql = ",\n    ".join(f"{name} {definition}" for name, definition in columns)
        connection.execute(text(f"CREATE TABLE IF NOT EXISTS {table_name} (\n    {columns_sql}\n)"))

    def build_table(table_name: str, columns: list[tuple[str, str]]):
        metadata = MetaData()
        built_columns = []
        for name, definition in columns:
            is_pk = "PRIMARY KEY" in definition
            sql_type = definition.replace(" PRIMARY KEY", "")
            built_columns.append(Column(name, type_map[TYPE_MAP[sql_type]](), primary_key=is_pk))
        return Table(table_name, metadata, *built_columns)

    def upsert_table(connection, table_name: str, columns: list[tuple[str, str]], rows: list[dict]) -> int:
        if not rows:
            return 0
        table = build_table(table_name, columns)
        stmt = insert(table).values(rows)
        primary_key = next(iter(table.primary_key.columns)).name
        update_columns = {column.name: stmt.excluded[column.name] for column in table.columns if column.name != primary_key}
        connection.execute(stmt.on_conflict_do_update(index_elements=[getattr(table.c, primary_key)], set_=update_columns))
        return len(rows)

    input_path = Path(input_dir)
    engine = create_db_engine()
    with engine.begin() as connection:
        for table_name, config in TABLES.items():
            ensure_schema(connection, table_name, config["columns"])
            count = upsert_table(connection, table_name, config["columns"], read_csv_rows(input_path / config["file"]))
            print(f"[OK] {table_name}: {count} filas upserted desde {input_path / config['file']}")
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga CSV consolidados a Supabase/Postgres")
    parser.add_argument("--input-dir", default=".", help="Directorio donde estan los CSV consolidados")
    parser.add_argument("--verify-only", action="store_true", help="Solo valida lectura de CSV y conexion de variables")
    args = parser.parse_args()
    run_load(input_dir=args.input_dir, verify_only=args.verify_only)


if __name__ == "__main__":
    main()
