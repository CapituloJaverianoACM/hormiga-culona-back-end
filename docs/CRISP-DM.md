# CRISP-DM — Hormiga Culona
## IA sobre datos de presupuesto público — Datos Abiertos Colombia (Bucaramanga)

---

## Fase I — Business Understanding

### 1.1 Objetivo de negocio

[Datos Abiertos Colombia](https://www.datos.gov.co/) es la plataforma del
gobierno donde se publican datos públicos (presupuesto municipal, casos de
infección, datos satelitales, etc.). En particular, los datos de **egresos e
ingresos del Presupuesto General del Municipio de Bucaramanga** se publican
como archivos Excel/CSV extensos, con un formato pensado para exportación
contable y no para consulta ciudadana: códigos sin documentación, valores
centinela numéricos (`-88`, `-98`) en vez de vacíos, bloques semestrales
pegados uno tras otro sin separación clara.

**Problema:** esta forma de publicar los datos los hace, en la práctica,
inaccesibles para cualquier persona sin conocimientos técnicos o de
presupuesto público.

**Objetivo del proyecto:** construir una solución basada en IA que permita a
cualquier ciudadano hacer preguntas en lenguaje natural sobre los gastos e
ingresos del municipio y obtener respuestas correctas, sin tener que abrir ni
interpretar los archivos originales.

### 1.2 Criterios de éxito

- Un usuario sin conocimientos técnicos puede hacer una pregunta (ej. "¿cuánto
  se ejecutó del presupuesto de 2023?") y obtener una respuesta correcta.
- Las respuestas deben ser trazables al dato fuente (año, periodo semestral,
  archivo de origen) para poder auditarlas.
- El sistema no debe inventar cifras cuando el dato no existe o es ambiguo.

### 1.3 Alcance inicial

- Datasets: `RESUMEN_EGRESOS_PRESUPUESTO_GENERAL_DEL_MUNICIPIO_DE_BUCARAMANGA`
  y `RESUMEN_INGRESOS_PRESUPUESTO_GENERAL_DE_BUCARAMANGA`.
- Periodo cubierto: semestres desde 2017-2 hasta 2025-1.
- Fuera de alcance por ahora: otros datasets de Datos Abiertos (infecciones,
  datos satelitales, etc.) — se evaluará como fase futura del proyecto.

---

## Fase II — Data Understanding

### 2.1 Recolección inicial de datos

Se descargaron los dos archivos CSV directamente de Datos Abiertos Colombia:
- `RESUMEN_EGRESOS_PRESUPUESTO_GENERAL_DEL_MUNICIPIO_DE_BUCARAMANGA_20260708.csv`
- `RESUMEN_INGRESOS_PRESUPUESTO_GENERAL_DE_BUCARAMANGA_20260708.csv`

### 2.2 Descripción de los datos

| | Egresos | Ingresos |
|---|---|---|
| Filas totales (crudas) | 39,752 | 3,968 |
| Columnas por fila | 15 | 12 |
| Encoding | utf-8 | utf-8 |
| Semestres detectados | 17 (2017-2 → 2025-1) | 16 (2017-2 → 2025-1) |

Ambos archivos vienen con **todos los semestres pegados uno tras otro** en
un solo CSV, separados por una fila-marcador de texto libre (ej. "GASTOS A
31 DICIEMBRE 2017"), en vez de venir un archivo por periodo. Las columnas no
tienen encabezado documentado oficialmente — el significado de cada columna
se infirió por inspección manual.

### 2.3 Exploración de datos (EDA)

Se construyó `eda_previo.py`, que recorre los datos crudos, antes de
cualquier limpieza, y genera evidencia visual y estadística:

- **Prevalencia de valores centinela** (candidatos a "nulo"): entre 24.2% y
  96.6% según la columna, en ambos datasets. Los valores encontrados fueron
  consistentemente `-88`, `-98` y variantes, además de guiones sueltos (`-`).
- **Distribución y outliers:** las columnas monetarias muestran outliers
  extremos pero en general plausibles para un presupuesto municipal.
- **Distribución de anchos de fila:** 100% de las filas en ambos archivos
  coincide con el ancho esperado (15 columnas en egresos, 12 en ingresos).

---

## Fase III — Data Preparation

Implementada en `data_processing.py`.

### 3.1 Selección de datos

Se descartan:
- **Código/rubro crudo** (columna 0 en ambos archivos): sin documentación
  oficial disponible sobre su nomenclatura.
- **Columna 12 de egresos**: siempre vacía o `-88` en todos los periodos
  revisados.

### 3.2 Limpieza de datos

- **Valores centinela → nulo:** el conjunto `SENTINELAS_VACIO` (`-88`, `-98`
  y variantes, `-`, `--`, vacío, `NA`, `NULL`) se convierte a `""`.
- **Separador decimal/miles:** lógica que detecta si la coma o el punto es
  el separador decimal según su posición y cantidad de dígitos.
- **Encoding:** detectado automáticamente por archivo con `chardet`.
- **Filas de leyenda/relleno:** al inicio de cada bloque semestral, se
  descartan filas con descripción vacía o "NO APLICA" hasta encontrar la
  primera fila con datos reales.
- **Anchos de fila irregulares:** se rellenan o truncan filas que no
  coincidan con el ancho esperado (código defensivo).

### 3.3 Construcción de datos

Cada fila de salida se enriquece con `id` (trazable, ej.
`egr-2018-1-00042`), `anio`, `periodo` y `archivo_origen`.

### 3.4 Integración de datos

Egresos e ingresos se procesan y consolidan por separado, generando
`egresos_consolidado.csv` e `ingresos_consolidado.csv`.

### 3.5 Formato de datos

Salida estandarizada en CSV, encoding `utf-8`, valores numéricos como texto
decimal estándar (punto como separador decimal).

### 3.6 Trazabilidad de la corrida

Cada ejecución genera `validacion_consolidacion.txt` con el detalle de
semestres detectados, filas de datos, filas descartadas y filas
problemáticas por archivo.

---

## Fase IV — Modeling

### 4.1 Selección de la técnica de modelado

**No se usó RAG.** Se descartó porque los datos ya son estructurados (tablas
en Postgres) — un vector store con embeddings no aporta nada cuando el dato
ya vive en filas y columnas con esquema conocido.

**Enfoque real: arquitectura de agentes** (`AgentOrchestratorService`), con
tres piezas especializadas:

| Agente | Responsabilidad |
|---|---|
| `queryAgent` | responde preguntas en lenguaje natural, con la tool `sql_query`, manteniendo contexto conversacional |
| `UIAgent` | traduce la solicitud a un `UIPlan` (JSON con `title`, `component`, `sql`, `summary`) para tablas/gráficos en el frontend |
| `ResultAgent` | toma resultados ya consultados y los resume en `explanation` (texto/UI) y `voice_reply` (audio) |

El orquestador decide el flujo según el canal: modo `response` (chat corto),
modo `ui` (reporte/gráfico estructurado), o modo `audio` (transcripción →
uno de los dos anteriores → síntesis de voz).

**Modelo:** GPT-5-mini, servido vía Azure AI Foundry — económico y rápido,
suficiente para las tareas actuales de generar SQL de solo lectura y narrar
resultados.

**Herramienta del agente:** `sql_query`, que hace `POST` a `/agent/sql`,
permitiendo que el agente ejecute consultas de solo lectura a través del
propio backend.

**Contexto de esquema:** `SchemaCacheService` mantiene en RAM el esquema de
las tablas junto con descripciones humanas, refrescándose cada hora vía
`APScheduler`.

### 4.2 Construcción del modelo

No hay entrenamiento ni fine-tuning propio: se usa GPT-5-mini pre-entrenado,
orquestado mediante el sistema de agentes descrito arriba.

### 4.3 Evaluación técnica del modelo

Cubierta por la suite de tests existente (`tests/agents/`, `tests/audio/`,
`tests/full_system_test/`). Adicionalmente, `AgentDatabaseService` valida en
tiempo de ejecución que cualquier SQL generado sea de solo lectura (solo
permite `SELECT`/`WITH`, bloquea `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER`/
`TRUNCATE`/`CREATE`).

---

## Fase V — Evaluation

### 5.1 Evaluar resultados

Existen dos capas de evaluación:
1. **Evaluación técnica/funcional** (automatizada): los tests confirman que
   el sistema corre de punta a punta sin errores.
2. **Evaluación de exactitud de contenido** (manual): revisión de que la
   lógica del SQL generado tenga sentido y que la respuesta corresponda con
   lo que arroja la base.

### 5.2 Revisar el proceso

El sistema ya cuenta con salvaguardas técnicas relevantes: solo lectura
forzada en SQL, cache de esquema actualizado, y separación clara entre modo
conversacional y modo UI.

---

## Fase VI — Deployment

### 6.1 Plan de despliegue

**Estado: ya corriendo (demo/producción).** Backend en FastAPI, empaquetado
en Docker (`python:3.14-slim`, expone puerto `8000`, arranca con `uvicorn
main:app`). Expone tres canales: chat texto (`/agent/chat`), generación de
datos para UI (`/agent/ui`), y voz por HTTP y WebSocket
(`/agent/audio/transcription`, `/agent/audio/synthesis`,
`/ws/agent/voice/{session_id}`).

### 6.2 Monitoreo y mantenimiento

- **Refresco de datos:** pipeline ETL con Airflow (`budget_pipeline`,
  tareas `extract` → `process` → `load`) que descarga, procesa y carga los
  datasets desde `datos.gov.co` a Supabase/Postgres.
- **Refresco de esquema:** `SchemaCacheService` se refresca cada hora
  automáticamente.

### 6.3 Reporte final

Este documento constituye el reporte final del proyecto Hormiga Culona para
este ciclo de CRISP-DM.

---

## Observaciones para Harry

Hay detallitos miralos porque conocés mejor el
detalle de cómo quedó armado el pipeline:

- No estoy seguro si el DAG de Airflow (`budget_pipeline`) está programado
  para correr solo automáticamente cada cierto tiempo o si por ahora hay que
  dispararlo a mano.
- Todavía no hicimos la retrospectiva del proyecto (qué salió bien, qué
  cambiaríamos) seria bueno que lo hicieras