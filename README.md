# Hormiga Culona Back End

Backend en **FastAPI** para consultas sobre datos presupuestales de Bucaramanga usando tres canales:

- **chat** en texto
- **generación de datos para UI**
- **voz** por HTTP y WebSocket

Además incluye un **pipeline ETL con Airflow** para descargar, limpiar y cargar datasets públicos a Supabase/Postgres.

---

## 1. Qué resuelve este proyecto

Este repositorio conecta cuatro piezas:

1. **Un API HTTP/WebSocket** que recibe preguntas del usuario.
2. **Un conjunto de agentes** que convierten la intención del usuario en respuestas, planes UI o narrativas.
3. **Una base de datos Postgres/Supabase** con datos presupuestales ya cargados.
4. **Un pipeline ETL** que descarga los datos fuente desde `datos.gov.co`, los consolida y los sube a la base.

En corto:

- el usuario pregunta por texto o audio,
- el backend interpreta la solicitud,
- consulta la base o genera una consulta SQL de solo lectura,
- devuelve respuesta textual, estructura para frontend o audio sintetizado.

---

## 2. Arquitectura general

```text
Usuario / Frontend
   │
   ├── HTTP POST /agent/chat
   ├── HTTP POST /agent/ui
   ├── HTTP POST /agent/audio/transcription
   ├── HTTP POST /agent/audio/synthesis
   └── WS   /ws/agent/voice/{session_id}
            │
            ▼
        FastAPI app
        app.py / main.py
            │
            ▼
   AgentOrchestratorService
            │
   ┌────────┼───────────────┬───────────────┐
   │        │               │               │
   ▼        ▼               ▼               ▼
Memory   AudioService   ResponseService   UIService
   │        │               │               │
   │        │               │               ├── UIAgent
   │        │               │               ├── ResultAgent
   │        │               │               └── AgentDatabaseService
   │        │               │
   │        │               └── queryAgent
   │        │
   │        ├── AzureTranscriptionClient
   │        └── AzureSpeechSynthesisClient
   │
   ▼
SchemaCacheService ──► AgentDatabaseService ──► SQLAlchemy engine ──► Supabase/Postgres
```

---

## 3. Componentes principales

### 3.1 Capa de entrada HTTP/WebSocket

**Archivos:**
- `main.py`
- `app.py`
- `api_routes.py`

**Responsabilidad:**
- crear la app FastAPI
- registrar rutas
- iniciar servicios compartidos en `lifespan`
- refrescar en memoria el esquema de base de datos
- exponer endpoints HTTP y canal WebSocket

### 3.2 Orquestador

**Archivo:** `services/orchestrator.py`

**Clase principal:** `AgentOrchestratorService`

Es el router central del backend. Decide qué flujo ejecutar según el canal:

- **response mode**: respuesta conversacional corta
- **ui mode**: plan de datos para frontend
- **audio mode**: transcripción + respuesta + síntesis

Instancia y coordina:

- `OpenAiClient`
- `queryAgent`
- `UIAgent`
- `ResultAgent`
- `AgentDatabaseService`
- `SchemaCacheService`
- `AgentAudioService`
- `AgentMemoryService`
- `AgentResponseService`
- `AgentUIService`

### 3.3 Agentes

**Carpeta:** `AI/agents/`

#### `queryAgent`
**Archivo:** `AI/agents/query_agent.py`

- responde preguntas del usuario en lenguaje natural
- puede usar la tool `sql_query`
- mantiene contexto conversacional con `InMemoryHistoryProvider`
- está pensado para respuestas breves y entendibles

#### `UIAgent`
**Archivo:** `AI/agents/ui_agent.py`

- traduce una solicitud del usuario a un `UIPlan`
- devuelve JSON estructurado con:
  - `title`
  - `component`
  - `sql`
  - `summary`
- el `component` puede ser:
  - `table`
  - `bar_chart`
  - `line_chart`
  - `card`
  - `list`

#### `ResultAgent`
**Archivo:** `AI/agents/result_agent.py`

- toma resultados ya consultados
- los resume para dos salidas:
  - `explanation` para UI/API
  - `voice_reply` para audio

#### `BaseAgent`
**Archivo:** `AI/agents/base_agent.py`

- base mínima para inyectar prompt limpio y unificado

#### Tool SQL del agente
**Archivo:** `AI/agents/tools/sql_query.py`

- hace `POST` hacia `http://127.0.0.1:8000/agent/sql`
- permite que el agente ejecute consultas de solo lectura a través del propio backend

### 3.4 Servicios de negocio

**Carpeta:** `services/`

#### `AgentResponseService`
**Archivo:** `services/response_service.py`

- usa `queryAgent`
- arma el payload de respuesta conversacional
- hoy devuelve una estructura simple con:
  - `summary`
  - `explanation`
  - `voice_reply`
  - `sql` vacío
  - previews vacíos

#### `AgentUIService`
**Archivo:** `services/ui_service.py`

- usa `UIAgent` para generar SQL + metadata UI
- ejecuta primero una preview limitada
- luego ejecuta la consulta completa
- usa `ResultAgent` para narrar el resultado
- devuelve:
  - título
  - tipo de componente
  - SQL
  - columnas
  - preview de filas
  - filas completas
  - cantidad de filas
  - explicación y respuesta corta de voz

#### `AgentAudioService`
**Archivo:** `services/audio_service.py`

- encapsula transcripción y síntesis
- delega en clientes de Azure Speech

#### `AgentMemoryService`
**Archivo:** `services/memory_service.py`

- guarda sesiones en memoria RAM
- separa sesiones por `scope:conversation_id`
- permite continuidad conversacional en modo `response`

#### `AgentDatabaseService`
**Archivo:** `services/database.py`

- ejecuta SQL sobre la base
- **valida que la consulta sea de solo lectura**
- solo permite consultas que arranquen con `SELECT` o `WITH`
- bloquea tokens peligrosos como:
  - `INSERT`
  - `UPDATE`
  - `DELETE`
  - `DROP`
  - `ALTER`
  - `TRUNCATE`
  - `CREATE`
  - etc.
- tiene dos métodos principales:
  - `execute_read_only_query`
  - `execute_preview_query`

#### `SchemaCacheService`
**Archivo:** `services/schema.py`

- singleton en memoria
- consulta `information_schema.columns`
- trae descripciones desde `public.data_base_descriptions`
- mantiene cache con:
  - estado
  - nombre base
  - esquema de tablas
  - descripción por tabla
- se refresca al arranque y luego cada hora con `APScheduler`

### 3.5 Infraestructura de datos

#### Engine SQLAlchemy
**Archivo:** `core/database.py`

- carga `DATABASE_URL`
- crea engine SQLAlchemy con pool
- parámetros actuales:
  - `pool_size=5`
  - `max_overflow=10`
  - `pool_timeout=30`
  - `pool_recycle=1800`

#### Schemas Pydantic
**Carpeta:** `schemas/`

- `schemas/message.py`: payload de chat
- `schemas/ui.py`: contratos de UI y narración
- `schemas/audio.py`: payload de síntesis
- `schemas/database.py`: payload de SQL y preview

### 3.6 Clientes externos

#### Azure AI Foundry / modelo
**Archivo:** `AI/open_ai_client.py`

Lee:
- `FOUNDRY_PROJECT_ENDPOINT`
- `FOUNDRY_MODEL_DEPLOYMENT_NAME`
- `AZURE_AI_FOUNDRY_API_KEY`

#### Azure Speech
**Archivo:** `AI/audio_client.py`

Incluye:
- `AzureTranscriptionClient`
- `AzureSpeechSynthesisClient`

Lee:
- `AZURE_SPEECH_ENDPOINT`
- `AZURE_SPEECH_API_KEY` o fallback a `AZURE_AI_FOUNDRY_API_KEY`
- `AZURE_SPEECH_REGION`
- `AZURE_SPEECH_TTS_ENDPOINT`
- `AZURE_SPEECH_VOICE`
- `AZURE_SPEECH_OUTPUT_FORMAT`

---

## 4. Flujo de ejecución por canal

### 4.1 Chat HTTP

**Endpoint:** `POST /agent/chat`

Flujo:

1. FastAPI recibe `content` y `sender_id`.
2. `AgentOrchestratorService.processMessage()` entra en modo `response`.
3. `AgentMemoryService` recupera o crea sesión.
4. `queryAgent` responde usando contexto y, si hace falta, SQL de solo lectura.
5. Se devuelve un JSON con resumen/respuesta.

### 4.2 UI HTTP

**Endpoint:** `POST /agent/ui`

Flujo:

1. el usuario pide algo como un reporte o gráfico
2. `UIAgent` genera un plan con `title`, `component` y `sql`
3. `AgentDatabaseService` corre preview limitada
4. `AgentDatabaseService` corre consulta completa
5. `ResultAgent` resume el resultado
6. el backend devuelve payload listo para frontend

### 4.3 Voz HTTP

#### Transcripción
**Endpoint:** `POST /agent/audio/transcription`

- recibe archivo wav
- devuelve texto transcrito

#### Síntesis
**Endpoint:** `POST /agent/audio/synthesis`

- recibe texto
- devuelve bytes `audio/wav`

### 4.4 Voz WebSocket

**Endpoint:**

```text
/ws/agent/voice/{session_id}?mode=response|ui&output=audio|json|both&preview_limit=5
```

Flujo:

1. cliente abre WebSocket
2. envía texto o bytes de audio
3. si llega audio, se transcribe
4. según `mode` se ejecuta:
   - `response`
   - `ui`
5. según `output` el servidor responde con:
   - JSON
   - audio sintetizado
   - ambos

Payload JSON devuelto:

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

---

## 5. API disponible

### Health check

- `GET /ping`

### Agente

- `POST /agent/chat`
- `POST /agent/sql`
- `GET /agent/description`
- `POST /agent/ui`
- `POST /agent/audio/synthesis`
- `POST /agent/audio/transcription`
- `WS /ws/agent/voice/{session_id}`

### Ejemplos rápidos

#### Ping

```bash
curl http://127.0.0.1:8000/ping
```

#### Chat

```bash
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "content": "Hola, dime los gastos de 2017",
    "sender_id": "demo-user"
  }'
```

#### SQL read-only

```bash
curl -X POST http://127.0.0.1:8000/agent/sql \
  -H 'Content-Type: application/json' \
  -d '{
    "sql_query": "SELECT * FROM egresos LIMIT 5"
  }'
```

#### UI

```bash
curl -X POST http://127.0.0.1:8000/agent/ui \
  -H 'Content-Type: application/json' \
  -d '{
    "content": "Hazme un reporte de gastos por año",
    "preview_limit": 5
  }'
```

#### Descripción del esquema cacheado

```bash
curl http://127.0.0.1:8000/agent/description
```

---

## 6. Pipeline ETL

El repo también contiene un pipeline para poblar la base de datos.

### Objetivo del pipeline

1. descargar datasets públicos de ingresos y egresos
2. extraer metadata descriptiva
3. consolidar archivos crudos que contienen múltiples cortes semestrales
4. normalizar columnas y valores
5. cargar tablas a Supabase/Postgres con upsert

### Origen de datos

Datasets usados:

- ingresos: `44kq-qq64`
- egresos: `ys3r-h9d3`

Fuentes:

- `https://www.datos.gov.co/api/views/44kq-qq64/rows.csv?accessType=DOWNLOAD`
- `https://www.datos.gov.co/api/views/ys3r-h9d3/rows.csv?accessType=DOWNLOAD`
- `https://www.datos.gov.co/api/views/<dataset_id>.json`

### Scripts del pipeline

#### `scripts/data_extraction.py`

- descarga CSVs crudos
- descarga metadata JSON
- genera `data_base_descriptions.csv`

Salida típica:
- CSV de ingresos
- CSV de egresos
- `data_base_descriptions.csv`

#### `scripts/data_processing.py`

- detecta encoding
- detecta bloques semestrales dentro del mismo CSV
- elimina filas basura o marcadores
- limpia números y centinelas
- consolida a formato tabular usable

Salida:
- `egresos_consolidado.csv`
- `ingresos_consolidado.csv`
- `validacion_consolidacion.txt`
- copia `data_base_descriptions.csv`

#### `scripts/load_to_supabase.py`

- valida archivos de entrada
- asegura esquema de tablas si no existe
- hace upsert en Postgres/Supabase

Tablas usadas:
- `data_base_descriptions`
- `ingresos`
- `egresos`

### DAG de Airflow

**Archivo:** `airflow/dags/budget_pipeline.py`

Tareas:

1. `extract`
2. `process`
3. `load`

Secuencia:

```text
extract >> process >> load
```

Frecuencia actual:
- `@daily`

Reintentos:
- `2`

---

## 7. Estructura del repositorio

```text
.
├── AI/
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── query_agent.py
│   │   ├── result_agent.py
│   │   ├── ui_agent.py
│   │   └── tools/sql_query.py
│   ├── audio_client.py
│   └── open_ai_client.py
├── airflow/
│   ├── airflow.cfg
│   ├── airflow.db
│   └── dags/budget_pipeline.py
├── core/
│   └── database.py
├── schemas/
│   ├── audio.py
│   ├── database.py
│   ├── message.py
│   └── ui.py
├── scripts/
│   ├── data_extraction.py
│   ├── data_processing.py
│   ├── load_to_supabase.py
│   └── database_schema.py
├── services/
│   ├── audio_service.py
│   ├── database.py
│   ├── memory_service.py
│   ├── orchestrator.py
│   ├── response_service.py
│   ├── schema.py
│   └── ui_service.py
├── tests/
│   ├── agents/
│   ├── audio/
│   ├── full_system_test/
│   └── tools/
├── app.py
├── api_routes.py
├── main.py
├── Dockerfile
├── requirements.txt
├── requirements-airflow.txt
└── .env.example
```

---

## 8. Variables de entorno

Copia `.env.example` a `.env`.

### Variables mínimas para el API

```env
FOUNDRY_PROJECT_ENDPOINT=https://<your-ai-services-account>.services.ai.azure.com/api/projects/<project-name>
FOUNDRY_MODEL_DEPLOYMENT_NAME=<model-deployment-name>
AZURE_AI_FOUNDRY_API_KEY=<your-api-key>
AZURE_SPEECH_ENDPOINT=<your-speech-service-endpoint>
AZURE_SPEECH_API_KEY=<your-speech-api-key-or-reuse-ai-foundry-key>
DATABASE_URL=<your-database-url>
```

### Variables útiles de voz

```env
AZURE_SPEECH_REGION=<speech-region-if-needed-for-tts>
AZURE_SPEECH_TTS_ENDPOINT=<optional-full-tts-endpoint>
AZURE_SPEECH_VOICE=es-CO-GonzaloNeural
AZURE_SPEECH_OUTPUT_FORMAT=riff-24khz-16bit-mono-pcm
```

### Variables para pipeline

```env
DATABASE_URL_PIPELINE=<your-pipeline-database-url>
PIPELINE_RAW_DIR=./data/raw
PIPELINE_PROCESSED_DIR=./data/processed
```

---

## 9. Docker

**Archivo:** `Dockerfile`

La imagen:

- usa `python:3.14-slim`
- instala `requirements.txt`
- copia:
  - `core/`
  - `schemas/`
  - `services/`
  - `AI/`
  - `scripts/`
  - `main.py`
- expone `8000`
- arranca con `uvicorn main:app --host 0.0.0.0 --port 8000`

### Build

```bash
docker build -t hormiga-culona-back-end .
```

### Run

```bash
docker run --rm -p 8000:8000 --env-file .env hormiga-culona-back-end
```

---

## 10. Tests

Hay varias capas de pruebas en `tests/`.

### `tests/agents/`
Pruebas unitarias y de comportamiento de agentes/servicios.

### `tests/audio/`
Pruebas de roundtrip de audio y artefactos generados.

### `tests/full_system_test/`
Scripts pequeños contra endpoints reales HTTP/WebSocket.

Precondiciones indicadas por el propio repo:
- servidor arriba en `http://127.0.0.1:8000`
- `.env` listo
- base accesible
- Azure Speech funcionando

### Comandos útiles

#### Pytest simple

```bash
pytest -q
```

#### Roundtrip de audio

```bash
python tests/audio/test_roundtrip.py --mode response --output both
```

#### Variantes

```bash
python tests/audio/test_roundtrip.py --mode ui --output json
python tests/audio/test_roundtrip.py --prompt "Hola dime los gastos de 2017" --mode response --output both
```

#### Full system

```bash
bash tests/full_system_test/run_all.sh
```

---

## 11. Decisiones de diseño visibles en el código

### Solo lectura para SQL
El backend no deja ejecutar SQL arbitrario de escritura desde el agente ni desde `/agent/sql`.

### Cache de esquema en RAM
El esquema no se consulta en cada request; se mantiene cacheado y se refresca cada hora.

### Separación por responsabilidad
La lógica está bastante separada en:
- entrada API
- orquestación
- agentes
- acceso a DB
- audio
- memoria
- ETL

### UI y conversación no son exactamente el mismo flujo
- `response` prioriza respuesta corta al usuario
- `ui` prioriza estructura para frontend + narración del resultado

### Voz reutiliza texto
El canal de audio no inventa una ruta paralela: primero transcribe a texto, luego usa el mismo flujo principal y al final sintetiza la respuesta.

---

## 12. Forma completa de correr el proyecto

Esta es la guía más directa para dejar todo funcionando de punta a punta.

### Opción A: correr solo el backend API

#### 1) Crear entorno virtual

```bash
python -m venv .venv
source .venv/bin/activate
```

#### 2) Instalar dependencias

```bash
pip install -r requirements.txt
```

#### 3) Crear `.env`

```bash
cp .env.example .env
```

Luego completa como mínimo:

```env
DATABASE_URL=postgresql://...
FOUNDRY_PROJECT_ENDPOINT=...
FOUNDRY_MODEL_DEPLOYMENT_NAME=...
AZURE_AI_FOUNDRY_API_KEY=...
AZURE_SPEECH_ENDPOINT=...
AZURE_SPEECH_API_KEY=...
```

Si también vas a usar pipeline:

```env
DATABASE_URL_PIPELINE=postgresql://...
PIPELINE_RAW_DIR=./data/raw
PIPELINE_PROCESSED_DIR=./data/processed
```

#### 4) Levantar el servidor

```bash
uvicorn main:app --reload
```

#### 5) Verificar que responde

```bash
curl http://127.0.0.1:8000/ping
```

Debe devolver algo como:

```json
{"status":"ok","message":"pong"}
```

#### 6) Verificar esquema cacheado

```bash
curl http://127.0.0.1:8000/agent/description
```

#### 7) Probar chat

```bash
curl -X POST http://127.0.0.1:8000/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "content": "Hola, dime los gastos de 2017",
    "sender_id": "demo-user"
  }'
```

#### 8) Probar UI

```bash
curl -X POST http://127.0.0.1:8000/agent/ui \
  -H 'Content-Type: application/json' \
  -d '{
    "content": "Hazme un reporte de gastos por año",
    "preview_limit": 5
  }'
```

#### 9) Probar síntesis de audio

```bash
curl -X POST http://127.0.0.1:8000/agent/audio/synthesis \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hola, esta es una prueba"}' \
  --output response.wav
```

#### 10) Probar transcripción

```bash
curl -X POST http://127.0.0.1:8000/agent/audio/transcription \
  -F 'file=@response.wav'
```

#### 11) Correr tests rápidos

```bash
pytest -q
```

Y si quieres flujo real de audio:

```bash
python tests/audio/test_roundtrip.py --mode response --output both
```

---

### Opción B: correr también el pipeline manualmente

Usa esto si todavía no quieres levantar Airflow y solo quieres poblar/validar datos.

#### 1) Extraer datos crudos

```bash
python scripts/data_extraction.py --output-dir data/raw/manual --run-label manual
```

#### 2) Procesar y consolidar

```bash
python scripts/data_processing.py --input-dir data/raw/manual --output-dir data/processed/manual
```

#### 3) Verificar antes de cargar

```bash
python scripts/load_to_supabase.py --input-dir data/processed/manual --verify-only
```

#### 4) Cargar a la base

```bash
python scripts/load_to_supabase.py --input-dir data/processed/manual
```

#### 5) Validar en la base

```sql
select * from data_base_descriptions;
select count(*) from ingresos;
select count(*) from egresos;
```

---

### Opción C: correr Airflow localmente

#### 1) Instalar dependencias de Airflow

```bash
pip install -r requirements-airflow.txt
```

#### 2) Configurar variables de sesión

```bash
source .venv/bin/activate
export AIRFLOW_HOME="$(pwd)/airflow"
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:///$AIRFLOW_HOME/airflow.db"
mkdir -p "$AIRFLOW_HOME"
```

#### 3) Inicializar Airflow

```bash
airflow db init
```

#### 4) Verificar que el DAG existe

```bash
airflow dags list | grep budget_pipeline
airflow tasks list budget_pipeline
```

#### 5) Probar tareas una por una

```bash
airflow tasks test budget_pipeline extract 2025-07-13
airflow tasks test budget_pipeline process 2025-07-13
airflow tasks test budget_pipeline load 2025-07-13
```

#### 6) Levantar webserver

```bash
airflow webserver
```

#### 7) En otra terminal, levantar scheduler

```bash
source .venv/bin/activate
export AIRFLOW_HOME="$(pwd)/airflow"
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="sqlite:///$AIRFLOW_HOME/airflow.db"
airflow scheduler
```

#### 8) Disparar el DAG

```bash
airflow dags trigger budget_pipeline
```

---

### Opción D: correr con Docker

#### 1) Construir imagen

```bash
docker build -t hormiga-culona-back-end .
```

#### 2) Ejecutar contenedor

```bash
docker run --rm -p 8000:8000 --env-file .env hormiga-culona-back-end
```

#### 3) Probar salud

```bash
curl http://127.0.0.1:8000/ping
```

---

## 13. Resumen corto

Si solo quieres arrancar ya:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

Luego:

```bash
curl http://127.0.0.1:8000/ping
```

Y para pipeline manual:

```bash
python scripts/data_extraction.py --output-dir data/raw/manual --run-label manual
python scripts/data_processing.py --input-dir data/raw/manual --output-dir data/processed/manual
python scripts/load_to_supabase.py --input-dir data/processed/manual --verify-only
python scripts/load_to_supabase.py --input-dir data/processed/manual
```
