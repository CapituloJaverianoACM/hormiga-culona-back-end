# Frontend API Guide

Guía rápida para consumir el backend desde frontend.

## Regla simple

- **Casos con audio/voz:** usar **WebSocket** en `/ws/agent/voice/{session_id}`.
- **Casos solo texto:** usar endpoints HTTP simples (`/agent/chat` y `/agent/ui`).
- **Helpers de audio:** `/agent/audio/synthesis` y `/agent/audio/transcription` solo si de verdad los necesitan fuera del flujo principal.
- **No usar `/agent/sql` desde frontend de usuario final**; parece más una herramienta interna/debug.

---

## Base URL

```text
http://127.0.0.1:8000
```

WebSocket:

```text
ws://127.0.0.1:8000
```

---

## 1) Flujo recomendado para VOZ: WebSocket

## Endpoint

```text
/ws/agent/voice/{session_id}?mode=response|ui&output=audio|json|both&preview_limit=5
```

Ejemplo:

```text
ws://127.0.0.1:8000/ws/agent/voice/user-123?mode=response&output=both&preview_limit=5
```

## Path param

- `session_id`: identificador de sesión/conversación. Puede ser el id del usuario, chat o thread.

## Query params

- `mode`
  - `response`: respuesta tipo asistente conversacional.
  - `ui`: respuesta pensada para renderizar un componente UI con datos.
- `output`
  - `audio`: el backend responde solo audio.
  - `json`: el backend responde solo JSON.
  - `both`: el backend responde JSON y luego audio.
- `preview_limit`
  - entero entre `1` y `20`.
  - si mandan otro valor, el backend lo corrige al rango válido.

## Qué puede enviar el frontend

El cliente puede mandar por el socket:

- **text frame**: prompt en texto.
- **binary frame**: audio WAV en bytes.

## Qué devuelve el backend

Según `output`:

- `json` → un **text frame** con JSON.
- `audio` → un **binary frame** con audio WAV.
- `both` → **primero JSON** y **después audio**.

Ese orden (`json` → `audio`) está confirmado por los tests del repo.

## Cuándo usar cada combinación

### A. Voz a respuesta hablada
La opción más natural para micrófono/asistente.

```text
mode=response&output=both
```

- envían audio
- reciben JSON para UI/logs
- reciben audio para reproducir al usuario

### B. Voz a datos para pintar UI
Útil si el usuario habla y esperan tabla/gráfica.

```text
mode=ui&output=json
```

- envían audio
- reciben JSON estructurado con `rows`, `columns`, `sql`, etc.
- no necesitan audio de vuelta

### C. Texto por socket pero con audio de salida
Si quieren conservar un solo canal pero el usuario escribió en vez de hablar.

```text
mode=response&output=audio
```

---

## 2) JSON que devuelve el WebSocket

Forma general:

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

## Diferencia importante entre `mode=response` y `mode=ui`

### `mode=response`
`data` viene pensado para conversación. Incluye normalmente:

```json
{
  "agent_reply": "...",
  "summary": "...",
  "explanation": "...",
  "voice_reply": "...",
  "sql": "SELECT ...",
  "columns": ["..."],
  "preview_rows": [{"...": "..."}],
  "row_count": 10
}
```

**Ojo:** en WebSocket, cuando el modo es `response`, el backend **elimina `rows`** antes de responder. O sea: reciben resumen y preview, no el dataset completo.

### `mode=ui`
`data` viene listo para renderizar UI. Incluye:

```json
{
  "title": "Gastos por año",
  "component": "table",
  "summary": "...",
  "explanation": "...",
  "voice_reply": "...",
  "sql": "SELECT ...",
  "columns": ["year", "total"],
  "preview_rows": [{"year": 2017, "total": 1000}],
  "rows": [{"year": 2017, "total": 1000}],
  "row_count": 1
}
```

`component` puede ser uno de:

- `table`
- `bar_chart`
- `line_chart`
- `card`
- `list`

---

## 3) Ejemplo frontend con WebSocket

## Texto → JSON + audio

```js
const ws = new WebSocket(
  'ws://127.0.0.1:8000/ws/agent/voice/user-123?mode=response&output=both&preview_limit=5'
)

ws.binaryType = 'arraybuffer'

ws.onopen = () => {
  ws.send('Hola dime los gastos de 2017')
}

ws.onmessage = (event) => {
  if (typeof event.data === 'string') {
    const data = JSON.parse(event.data)
    console.log('JSON:', data)
    return
  }

  // audio wav
  const blob = new Blob([event.data], { type: 'audio/wav' })
  const url = URL.createObjectURL(blob)
  const audio = new Audio(url)
  audio.play()
}
```

## Audio → JSON + audio

```js
const ws = new WebSocket(
  'ws://127.0.0.1:8000/ws/agent/voice/user-123?mode=response&output=both&preview_limit=5'
)

ws.binaryType = 'arraybuffer'

ws.onopen = async () => {
  // wavArrayBuffer debe ser audio WAV completo
  ws.send(wavArrayBuffer)
}

ws.onmessage = (event) => {
  if (typeof event.data === 'string') {
    const payload = JSON.parse(event.data)
    console.log(payload)
    return
  }

  const blob = new Blob([event.data], { type: 'audio/wav' })
  const url = URL.createObjectURL(blob)
  new Audio(url).play()
}
```

## Recomendación práctica para frontend

Para voz usen por defecto:

```text
mode=response&output=both
```

Porque en un solo request obtienen:

- texto transcrito del usuario (`user_text`)
- respuesta estructurada (`JSON`)
- respuesta hablada (`audio`)

---

## 4) Endpoints HTTP para casos SOLO TEXTO

## `POST /agent/chat`

Uso: texto conversacional simple.

### Request

```json
{
  "content": "Hola dime los gastos de 2017",
  "sender_id": "user-123"
}
```

### Response

```json
{
  "agent_reply": "...",
  "summary": "...",
  "explanation": "...",
  "voice_reply": "...",
  "sql": "SELECT ...",
  "columns": ["..."],
  "preview_rows": [{"...": "..."}],
  "row_count": 10
}
```

### Cuándo usarlo

- chat escrito
- caja de texto simple
- no necesitan socket
- no necesitan audio

### Ejemplo frontend

```js
const res = await fetch('http://127.0.0.1:8000/agent/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    content: 'Hola dime los gastos de 2017',
    sender_id: 'user-123'
  })
})

const data = await res.json()
console.log(data)
```

---

## `POST /agent/ui`

Uso: texto que debe convertirse en data lista para renderizar componentes.

### Request

```json
{
  "content": "Haz un reporte simple de gastos por año",
  "preview_limit": 5
}
```

### Response

```json
{
  "title": "Gastos por año",
  "component": "table",
  "summary": "...",
  "explanation": "...",
  "voice_reply": "...",
  "sql": "SELECT ...",
  "columns": ["year", "total"],
  "preview_rows": [{"year": 2017, "total": 1000}],
  "rows": [{"year": 2017, "total": 1000}],
  "row_count": 1
}
```

### Cuándo usarlo

- dashboards
- tablas
- gráficas
- cards/listas
- el usuario escribió, no habló

### Ejemplo frontend

```js
const res = await fetch('http://127.0.0.1:8000/agent/ui', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    content: 'Haz un reporte simple de gastos por año',
    preview_limit: 5
  })
})

const data = await res.json()
console.log(data.component, data.rows)
```

---

## 5) Endpoints helper de audio

Estos no deberían ser el flujo principal si ya usan WebSocket para voz.

## `POST /agent/audio/synthesis`

Convierte texto a audio WAV.

### Request

```json
{
  "text": "Hola dime los gastos de 2017"
}
```

### Response

- body binario
- `Content-Type: audio/wav`

### Ejemplo

```js
const res = await fetch('http://127.0.0.1:8000/agent/audio/synthesis', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'Hola' })
})

const blob = await res.blob()
const url = URL.createObjectURL(blob)
new Audio(url).play()
```

## `POST /agent/audio/transcription`

Convierte audio a texto.

### Request

- `multipart/form-data`
- campo: `file`

### Response

```json
{
  "text": "Hola dime los gastos de 2017",
  "filename": "audio.wav",
  "content_type": "audio/wav"
}
```

### Ejemplo

```js
const form = new FormData()
form.append('file', file) // idealmente wav

const res = await fetch('http://127.0.0.1:8000/agent/audio/transcription', {
  method: 'POST',
  body: form
})

const data = await res.json()
console.log(data.text)
```

---

## 6) Endpoints auxiliares

## `GET /ping`

Health check.

### Response

```json
{
  "status": "ok",
  "message": "pong"
}
```

## `GET /agent/description`

Devuelve la descripción/cache del esquema de base de datos.

Útil para:

- debug
- inspección interna
- tooling

No parece necesario para el flujo normal del usuario final.

## `POST /agent/sql`

Ejecuta SQL de solo lectura.

### Request

```json
{
  "sql_query": "SELECT 1 AS ok"
}
```

### Response

```json
{
  "status": "success",
  "data": [
    { "ok": 1 }
  ]
}
```

### Importante

- solo acepta consultas de lectura (`SELECT`/`WITH`)
- rechaza queries vacías
- rechaza SQL de escritura/borrado
- **mejor no exponer esto al usuario final desde frontend**

---

## 7) Estrategia recomendada para el frontend

## Caso 1: chat escrito
Usar:

```text
POST /agent/chat
```

## Caso 2: texto que debe renderizar tabla/gráfica
Usar:

```text
POST /agent/ui
```

## Caso 3: usuario habla y espera respuesta hablada
Usar:

```text
WS /ws/agent/voice/{session_id}?mode=response&output=both
```

## Caso 4: usuario habla y esperan data para UI
Usar:

```text
WS /ws/agent/voice/{session_id}?mode=ui&output=json
```

## Caso 5: utilidades sueltas de audio
Usar solo si hace falta:

```text
POST /agent/audio/synthesis
POST /agent/audio/transcription
```

---

## 8) Notas importantes

- El WebSocket actual **no parece streaming por chunks**; funciona como request/response por mensaje.
- Si envían audio por socket, manden el archivo/audio completo como binario.
- Si usan `output=both`, esperen **dos mensajes**: primero JSON, luego audio.
- En `mode=response`, el WebSocket devuelve preview de datos, no todas las filas.
- En `mode=ui`, sí devuelve `rows` completas.
- `preview_limit` tiene rango real `1..20`.
- Los errores del WebSocket se devuelven como un `agent_result` con mensaje de error en `explanation` y, si `output` lo pide, también audio de error.

---

## 9) Recomendación final

Si el producto tiene micrófono o respuesta hablada:

- **usen WebSocket como camino principal**
- dejen HTTP para chat escrito/UI escrita
- tomen `/agent/audio/transcription` y `/agent/audio/synthesis` como helpers, no como flujo principal
