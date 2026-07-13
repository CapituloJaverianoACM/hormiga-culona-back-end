from scripts.data_extraction import build_csv_url, build_metadata_url
from scripts.load_to_supabase import parse_value


def test_build_csv_url_uses_socrata_download_endpoint():
    assert build_csv_url("44kq-qq64") == "https://www.datos.gov.co/api/views/44kq-qq64/rows.csv?accessType=DOWNLOAD"


def test_build_metadata_url_uses_socrata_metadata_endpoint():
    assert build_metadata_url("44kq-qq64") == "https://www.datos.gov.co/api/views/44kq-qq64.json"


def test_parse_value_handles_numeric_and_empty_values():
    assert parse_value("anio", "2024") == 2024
    assert parse_value("pct_ejecucion", "12.5") == 12.5
    assert parse_value("descripcion", "texto") == "texto"
    assert parse_value("data_base_name", "ingresos") == "ingresos"
    assert parse_value("descripcion", "") is None
