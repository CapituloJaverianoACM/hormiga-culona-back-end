import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.models import DAG
from airflow.operators.python import PythonOperator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.data_extraction import run_extract
from scripts.data_processing import run_processing
from scripts.load_to_supabase import run_load

RAW_ROOT = Path(os.getenv("PIPELINE_RAW_DIR", REPO_ROOT / "data" / "raw"))
PROCESSED_ROOT = Path(os.getenv("PIPELINE_PROCESSED_DIR", REPO_ROOT / "data" / "processed"))


def _run_paths(logical_date):
    run_label = logical_date.strftime("%Y%m%d")
    return run_label, RAW_ROOT / run_label, PROCESSED_ROOT / run_label


def extract_task(**context):
    run_label, raw_dir, _ = _run_paths(context["logical_date"])
    return run_extract(output_dir=str(raw_dir), run_label=run_label)


def process_task(**context):
    _, raw_dir, processed_dir = _run_paths(context["logical_date"])
    return run_processing(input_dir=str(raw_dir), output_dir=str(processed_dir))


def load_task(**context):
    _, _, processed_dir = _run_paths(context["logical_date"])
    return run_load(input_dir=str(processed_dir))


with DAG(
    dag_id="budget_pipeline",
    description="Extract, process and load Bucaramanga budget datasets",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["etl", "supabase", "bucaramanga"],
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_task)
    process = PythonOperator(task_id="process", python_callable=process_task)
    load = PythonOperator(task_id="load", python_callable=load_task)

    extract >> process >> load
