# hormiga-culona-back-end

Backend FastAPI para chat, UI y voz sobre consultas SQL.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Variables mínimas en `.env`:
- `DATABASE_URL`
- `DATABASE_URL_PIPELINE`
- `FOUNDRY_PROJECT_ENDPOINT`
- `FOUNDRY_MODEL_DEPLOYMENT_NAME`
- `AZURE_AI_FOUNDRY_API_KEY`
- `AZURE_SPEECH_ENDPOINT`
- `AZURE_SPEECH_API_KEY`

## Run server

```bash
uvicorn main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/ping
```

## HTTP endpoints

- `POST /agent/chat`
- `POST /agent/ui`
- `POST /agent/audio/transcription`
- `POST /agent/audio/synthesis`
- `GET /agent/description`

## WebSocket voice protocol

Endpoint:

```text
ws://127.0.0.1:8000/ws/agent/voice/{session_id}?mode=response|ui&output=audio|json|both&preview_limit=5
```

Query params:
- `mode=response|ui`
- `output=audio|json|both`
- `preview_limit=1..20`

Frame types:
- client can send a **text frame** with the user prompt
- client can send a **bytes frame** with audio wav payload
- server can return a **text frame** with JSON when `output=json|both`
- server can return a **bytes frame** with synthesized audio when `output=audio|both`

JSON payload shape returned by websocket:

```json
{
  "type": "agent_result",
  "mode": "response",
  "user_text": "hola",
  "voice_reply": "respuesta corta",
  "explanation": "explicación breve",
  "data": {}
}
```

## Run tests

Simple pytest run:

```bash
pytest -q
```

Roundtrip websocket test:

```bash
python tests/audio/test_roundtrip.py --mode response --output both
```

Useful variants:

```bash
python tests/audio/test_roundtrip.py --mode ui --output json
python tests/audio/test_roundtrip.py --prompt "Hola dime los gastos de 2017" --mode response --output both
```

Artifacts from the roundtrip test are written to `tests/audio/artifacts/` and ignored by git.

## ETL pipeline

This repo includes an Apache Airflow DAG for:
- extract raw budget datasets from datos.gov.co
- process them into consolidated CSVs
- load them into Supabase/Postgres using `DATABASE_URL_PIPELINE`

Install Airflow separately so the API app stays light:

```bash
pip install -r requirements-airflow.txt
```

Dataset sources:
- `https://www.datos.gov.co/api/views/44kq-qq64/rows.csv?accessType=DOWNLOAD`
- `https://www.datos.gov.co/api/views/ys3r-h9d3/rows.csv?accessType=DOWNLOAD`
- metadata descriptions from `https://www.datos.gov.co/api/views/<dataset_id>.json`

### Files and folders

- DAG: `airflow/dags/budget_pipeline.py`
- raw output: `data/raw/<yyyymmdd>/`
- processed output: `data/processed/<yyyymmdd>/`
- extraction script: `scripts/data_extraction.py`
- processing script: `scripts/data_processing.py`
- load script: `scripts/load_to_supabase.py`

### Required env vars

Add these to `.env`:

```env
DATABASE_URL_PIPELINE=postgresql://...
PIPELINE_RAW_DIR=./data/raw
PIPELINE_PROCESSED_DIR=./data/processed
```

Optional env vars:
- `PIPELINE_RAW_DIR` (default `./data/raw`)
- `PIPELINE_PROCESSED_DIR` (default `./data/processed`)

### First-time database setup

The pipeline user should be able to `INSERT` and `UPDATE` the target tables.
If the database user cannot create tables, create them once from Supabase SQL Editor and then reuse them.

Tables used by the loader:
- `data_base_descriptions(data_base_name, description)`
- `ingresos(...)`
- `egresos(...)`

### Run without Airflow

Use this first to validate the ETL locally:

```bash
python scripts/data_extraction.py --output-dir data/raw/manual --run-label manual
python scripts/data_processing.py --input-dir data/raw/manual --output-dir data/processed/manual
python scripts/load_to_supabase.py --input-dir data/processed/manual --verify-only
python scripts/load_to_supabase.py --input-dir data/processed/manual
```

The extract step also writes:
- `data_base_descriptions.csv`

The process step also copies that file into the processed folder.

### Deploy and test Apache Airflow locally

From the project root:

```bash
source .venv/bin/activate
export AIRFLOW_HOME="$(pwd)/airflow"
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:///$AIRFLOW_HOME/airflow.db"
mkdir -p "$AIRFLOW_HOME"
airflow db init
```

Check that the DAG is visible:

```bash
airflow dags list | grep budget_pipeline
airflow tasks list budget_pipeline
```

Test each task manually:

```bash
airflow tasks test budget_pipeline extract 2025-07-13
airflow tasks test budget_pipeline process 2025-07-13
airflow tasks test budget_pipeline load 2025-07-13
```

Expected task flow:
- `extract` writes raw CSVs and `data_base_descriptions.csv`
- `process` writes `ingresos_consolidado.csv`, `egresos_consolidado.csv`, `validacion_consolidacion.txt`, and copies `data_base_descriptions.csv`
- `load` upserts the 3 target tables

To run the scheduler and UI:

```bash
source .venv/bin/activate
export AIRFLOW_HOME="$(pwd)/airflow"
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:///$AIRFLOW_HOME/airflow.db"
airflow webserver
```

In another terminal:

```bash
source .venv/bin/activate
export AIRFLOW_HOME="$(pwd)/airflow"
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:///$AIRFLOW_HOME/airflow.db"
airflow scheduler
```

Then trigger the DAG:

```bash
airflow dags trigger budget_pipeline
```

### Verify in Supabase

Run these queries after a successful load:

```sql
select * from data_base_descriptions;
select count(*) from ingresos;
select count(*) from egresos;
```
