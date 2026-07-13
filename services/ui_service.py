import json
from typing import Any

from fastapi import HTTPException


class AgentUIService:
    def __init__(self, ui_agent, result_agent, db_service):
        self.ui_agent = ui_agent
        self.result_agent = result_agent
        self.db_service = db_service

    async def build_ui_data(self, content: str, preview_limit: int = 5) -> dict[str, Any]:
        plan = await self.ui_agent.run_agent(content)
        try:
            preview_rows = self.db_service.execute_preview_query(plan.sql, preview_limit)
        except HTTPException as exc:
            explanation = self._sql_error_explanation("No pude validar la consulta previa.", exc)
            return {
                "title": plan.title,
                "component": plan.component,
                "summary": "No pude preparar el resultado.",
                "explanation": explanation,
                "voice_reply": "No pude preparar la consulta.",
                "sql": plan.sql,
                "columns": [],
                "preview_rows": [],
                "rows": [],
                "row_count": 0,
            }

        try:
            rows = self.db_service.execute_read_only_query(plan.sql)
        except HTTPException as exc:
            explanation = self._sql_error_explanation("La consulta se construyó, pero falló al traer datos.", exc)
            return {
                "title": plan.title,
                "component": plan.component,
                "summary": "La consulta falló al traer datos.",
                "explanation": explanation,
                "voice_reply": "La consulta falló al traer datos.",
                "sql": plan.sql,
                "columns": [],
                "preview_rows": preview_rows,
                "rows": [],
                "row_count": 0,
            }

        columns = list(rows[0].keys()) if rows else list(preview_rows[0].keys()) if preview_rows else []
        narration = await self._narrate_result(content, plan.title, plan.component, plan.sql, columns, rows, preview_rows)
        return {
            "title": plan.title,
            "component": plan.component,
            "summary": narration["summary"],
            "explanation": narration["explanation"],
            "voice_reply": narration["voice_reply"],
            "sql": plan.sql,
            "columns": columns,
            "preview_rows": preview_rows,
            "rows": rows,
            "row_count": len(rows),
        }

    async def _narrate_result(
        self,
        user_request: str,
        title: str,
        component: str,
        sql: str,
        columns: list[str],
        rows: list[dict],
        preview_rows: list[dict],
    ) -> dict[str, str]:
        row_count = len(rows)
        sample_rows = self._compact_rows(preview_rows or rows, columns)
        prompt = "\n".join(
            [
                f"Solicitud del usuario: {user_request}",
                f"Título sugerido: {title}",
                f"Componente sugerido: {component}",
                f"Cantidad de filas: {row_count}",
                f"Columnas principales: {', '.join(columns[:6]) if columns else 'sin columnas'}",
                f"SQL usada: {sql}",
                "Muestra pequeña del resultado:",
                json.dumps(sample_rows, ensure_ascii=False),
                "Explica el hallazgo principal sin listar toda la base ni repetir filas completas.",
                "Usa español claro y accesible para cualquier persona.",
                "No uses notación matemática, LaTeX, fórmulas ni símbolos especiales.",
                "No menciones JSON en voice_reply; la respuesta de audio debe entenderse sola.",
            ]
        )
        try:
            narration = await self.result_agent.run_agent(prompt)
            return {
                "summary": narration.summary or self._fallback_summary(title, row_count),
                "explanation": narration.explanation.strip(),
                "voice_reply": narration.voice_reply.strip(),
            }
        except Exception:
            explanation = self._fallback_explanation(title, component, columns, rows, preview_rows)
            return {
                "summary": self._fallback_summary(title, row_count),
                "explanation": explanation,
                "voice_reply": self._fallback_voice_reply(title, rows, preview_rows),
            }

    def _compact_rows(self, rows: list[dict], columns: list[str], max_rows: int = 3, max_cols: int = 4) -> list[dict[str, Any]]:
        compact = []
        selected_columns = columns[:max_cols]
        for row in rows[:max_rows]:
            if not isinstance(row, dict) or "error" in row:
                continue
            keys = selected_columns or list(row.keys())[:max_cols]
            compact.append({key: self._json_safe(row.get(key)) for key in keys if key in row})
        return compact

    def _sql_error_explanation(self, prefix: str, error: HTTPException) -> str:
        detail = error.detail if isinstance(error.detail, str) else str(error.detail)
        return f"{prefix} {detail}".strip()

    def _json_safe(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    def _fallback_summary(self, title: str, row_count: int) -> str:
        if row_count == 0:
            return "No encontré filas para mostrar."
        return self._short_text(f"{title or 'Resultado listo'} con {row_count} filas.", 60)

    def _fallback_explanation(
        self,
        title: str,
        component: str,
        columns: list[str],
        rows: list[dict],
        preview_rows: list[dict],
    ) -> str:
        row_count = len(rows)
        first_row = next((row for row in preview_rows if isinstance(row, dict) and "error" not in row), None)
        columns_text = ", ".join(self._short_text(col, 24) for col in columns[:4]) if columns else "sin columnas detectadas"
        sample = self._row_sample(first_row, columns)
        parts = [
            f"{self._short_text(title or 'Resultado generado', 80)} listo como {self._short_text(component or 'table', 20)}.",
            f"La consulta devolvió {row_count} filas y las columnas principales son {columns_text}.",
        ]
        if sample:
            parts.append(f"Muestra corta: {sample}.")
        elif row_count == 0:
            parts.append("No encontré registros para esa solicitud.")
        return " ".join(parts)

    def _fallback_voice_reply(self, title: str, rows: list[dict], preview_rows: list[dict]) -> str:
        row_count = len(rows)
        first_row = next((row for row in preview_rows if isinstance(row, dict) and "error" not in row), None)
        lead = self._row_lead(first_row, list(first_row.keys()) if first_row else [])
        if row_count == 0:
            return "No encontré resultados."
        parts = [
            f"{self._short_text(title or 'Resultado listo', 50)}.",
            f"Encontré {row_count} filas.",
        ]
        if lead:
            parts.append(f"Primer dato: {lead}.")
        return " ".join(parts)

    def _row_sample(self, row: dict[str, Any] | None, columns: list[str]) -> str:
        if not row:
            return ""
        pairs = []
        keys = columns[:2] or list(row.keys())[:2]
        for key in keys:
            if key not in row:
                continue
            text = self._short_text(row.get(key), 40)
            if text:
                pairs.append(f"{self._short_text(key, 24)}: {text}")
        return ", ".join(pairs)

    def _row_lead(self, row: dict[str, Any] | None, columns: list[str]) -> str:
        if not row:
            return ""
        for key in columns[:2] or list(row.keys())[:2]:
            if key not in row:
                continue
            value = row.get(key)
            if value is None:
                continue
            return f"{self._short_text(key, 18)} {self._short_text(value, 18)}"
        return ""

    def _short_text(self, value: Any, limit: int) -> str:
        text = str(value or "").strip().replace("\n", " ")
        while "  " in text:
            text = text.replace("  ", " ")
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."
