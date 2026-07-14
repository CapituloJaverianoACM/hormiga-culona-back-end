# CRISP-DM — Fases I, II y III
## Proyecto: IA sobre datos de presupuesto público — Datos Abiertos Colombia (Bucaramanga)

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
- El sistema no debe inventar cifras (riesgo de alucinación) cuando el dato
  no existe o es ambiguo.

### 1.3 Alcance inicial

- Datasets: `RESUMEN_EGRESOS_PRESUPUESTO_GENERAL_DEL_MUNICIPIO_DE_BUCARAMANGA`
  y `RESUMEN_INGRESOS_PRESUPUESTO_GENERAL_DE_BUCARAMANGA`.
- Periodo cubierto: semestres desde 2017-2 hasta 2025-1 (ver Fase II).
- Fuera de alcance por ahora: otros datasets de Datos Abiertos (infecciones,
  datos satelitales, etc.) — se evaluará como fase futura del proyecto.

### 1.4 Riesgos identificados

- **Calidad de la fuente:** los archivos originales tienen inconsistencias de
  formato (ver Fase II), lo que puede propagar errores si no se detectan a
  tiempo.
- **Alucinación del modelo de IA:** al conectar un LLM a la base de datos
  consolidada, existe riesgo de que genere cifras que no correspondan a los
  datos reales — se deberá validar en la fase de Evaluación (Fase V).

---

## Fase II — Data Understanding

### 2.1 Recolección inicial de datos

Se descargaron los dos archivos CSV directamente de Datos Abiertos
Colombia:
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
se infirió por inspección manual y quedó registrado como comentarios en el
mapeo de columnas (ver Fase III).

### 2.3 Exploración de datos (EDA)

Se construyó `eda_previo.py`, que recorre los datos **crudos, antes de
cualquier limpieza**, y genera evidencia visual y estadística:

**a) Prevalencia de valores centinela por columna** (candidatos a "nulo"):

| Columna (egresos) | % centinela | Columna (ingresos) | % centinela |
|---|---|---|---|
| presupuesto_definitivo | 96.6% | presupuesto_final | 81.0% |
| disponibilidad_acumulada | 93.3% | recaudo_acumulado | 77.8% |
| compromiso_acumulado | 92.8% | recaudos | 53.5% |
| presupuesto_inicial | 92.1% | presupuesto_inicial | 50.3% |
| pagos_acumulados | 91.7% | saldo_por_recaudar | 44.7% |
| saldo_reservas / contracreditos | 86.3% | adiciones | 39.2% |
| creditos | 86.3% | reducciones | 29.1% |
| adiciones | 85.8% | contracreditos | 27.9% |
| obligaciones | 83.2% | creditos | 27.7% |
| pct_ejecucion | 65.0% | pct_ejecucion | 24.2% |

Los valores centinela encontrados fueron consistentemente `-88`, `-98` y sus
variantes con decimales, además de guiones sueltos (`-`) — ningún valor
"sospechoso" adicional apareció fuera de ese patrón.

**b) Distribución y outliers (boxplots, escala simlog):** las columnas
monetarias muestran outliers extremos pero plausibles para un presupuesto
municipal (ej. `reducciones` en egresos llega a 116,909,579,656 — ~117 mil
millones de pesos), salvo dos excepciones marcadas como hallazgo (ver 2.4).

**c) Distribución de anchos de fila:** el 100% de las filas en ambos archivos
coincide con el ancho esperado (15 columnas en egresos, 12 en ingresos) — no
hay filas mal formadas en estos archivos específicos.

### 2.4 Verificación de calidad — hallazgos que requieren atención

1. **`pct_ejecucion` (ingresos) con valores hasta 1,318,040%** (mediana=100,
   promedio=595). Un porcentaje de ejecución no debería superar unos pocos
   cientos. Pendiente: revisar si es un error de captura en la fuente o un
   problema de parseo de separador decimal/miles, antes de usar esta columna
   en el sistema de consultas.
2. **Salto de escala entre `presupuesto_inicial` (mediana=0, máx=980) y
   `presupuesto_definitivo` (máx=3,715,410,683) en egresos** — en teoría
   representan la misma cifra en dos momentos del ciclo presupuestal.
   Pendiente: validar con criterio de dominio (Hacienda/Planeación
   municipal) si es un comportamiento esperado o un síntoma del mismo
   problema de parseo.

**Conclusión de calidad:** los datos son utilizables, pero **no se
consideran 100% verificados** en esas dos columnas hasta resolver los
hallazgos anteriores. Esto se documenta explícitamente para no dar una falsa
sensación de "todo validado" en fases posteriores.

---

## Fase III — Data Preparation

Implementada en `data_processing.py`. Cada decisión de esta fase está
respaldada por la evidencia de la Fase II (ver arriba).

### 3.1 Selección de datos

Se descartan dos tipos de columna:
- **Código/rubro crudo** (columna 0 en ambos archivos): sin documentación
  oficial disponible que explique su nomenclatura — incluirlo generaría un
  campo inútil o engañoso.
- **Columna 12 de egresos**: siempre vacía o `-88` en todos los periodos
  revisados.

### 3.2 Limpieza de datos

- **Valores centinela → nulo:** el conjunto `SENTINELAS_VACIO` (`-88`,
  `-98` y variantes, `-`, `--`, vacío, `NA`, `NULL`) se convierte a `""`.
  Justificado por la prevalencia encontrada en el EDA (24%–96.6% según
  columna).
- **Separador decimal/miles:** lógica que detecta si la coma o el punto es
  el separador decimal según su posición y cantidad de dígitos, dado que los
  exports no son consistentes entre sí (formato colombiano `1.234.567,89`
  vs. otros).
- **Encoding:** detectado automáticamente por archivo con `chardet`, ya que
  no todos los exports usan `utf-8`.
- **Filas de leyenda/relleno:** al inicio de cada bloque semestral, se
  descartan filas con descripción vacía o "NO APLICA" hasta encontrar la
  primera fila con datos reales.
- **Anchos de fila irregulares:** se rellenan (padding) o truncan filas que
  no coincidan con el ancho esperado — código defensivo que, según el EDA,
  no se activó en los archivos actuales (100% de consistencia), pero se
  mantiene para exports futuros.

### 3.3 Construcción de datos

Cada fila de salida se enriquece con:
- `id`: identificador único trazable (ej. `egr-2018-1-00042`)
- `anio` y `periodo`: extraídos del marcador de semestre detectado
- `archivo_origen`: nombre del CSV del que proviene

Esto permite rastrear cualquier fila hasta su origen exacto ante una
auditoría o duda futura.

### 3.4 Integración de datos

Egresos e ingresos se procesan y consolidan por separado (mismo pipeline,
mapeos distintos), generando:
- `egresos_consolidado.csv`
- `ingresos_consolidado.csv`

### 3.5 Formato de datos

Salida estandarizada en CSV con encabezado fijo (`id`, `anio`, `periodo`,
campos del mapeo, `archivo_origen`), codificación `utf-8`, valores numéricos
como texto decimal estándar (punto como separador decimal).

### 3.6 Trazabilidad de la corrida

Cada ejecución de `data_processing.py` genera `validacion_consolidacion.txt`
con: semestres detectados, total de filas de datos, filas de leyenda
descartadas, y filas con número de columnas distinto al esperado — por
archivo procesado.