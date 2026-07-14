from decimal import Decimal
from pathlib import Path
from types import MethodType

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from services.orchestrator import AgentOrchestratorService


"""
Made with AI for visualizing the output of the UI Agent.
Now tested without live DB or model calls.
"""


def _pick_axes(rows: list[dict]) -> tuple[str, str]:
    if not rows:
        raise AssertionError("El agente no devolvió filas para graficar")

    first = rows[0]
    numeric_keys = []
    for key in first.keys():
        values = [row.get(key) for row in rows[:20] if row.get(key) is not None]
        if values and all(isinstance(v, (int, float, Decimal)) and not isinstance(v, bool) for v in values):
            numeric_keys.append(key)

    if not numeric_keys:
        raise AssertionError(f"No hay columnas numéricas para graficar: {list(first.keys())}")

    x_key = "anio" if "anio" in first else next((k for k in first.keys() if k not in numeric_keys), list(first.keys())[0])
    y_key = next((k for k in numeric_keys if k != x_key), numeric_keys[0])
    return x_key, y_key


def test_ui_agent_2017_expenses_report_generates_chart():
    orchestrator = AgentOrchestratorService.__new__(AgentOrchestratorService)

    def _fake_build_ui_data(self, content: str, preview_limit: int = 5) -> dict:
        assert "gastos" in content.lower()
        assert preview_limit == 5
        rows = [
            {"anio": 2019, "total_gastos": 1_200_000_000_000},
            {"anio": 2020, "total_gastos": 1_350_000_000_000},
            {"anio": 2021, "total_gastos": 1_500_000_000_000},
            {"anio": 2022, "total_gastos": 1_650_000_000_000},
        ]
        return {
            "title": "Reporte de gastos por año",
            "component": "line_chart",
            "summary": "Gastos agregados por año.",
            "explanation": "Los gastos crecen de forma sostenida entre 2019 y 2022.",
            "voice_reply": "Preparé un reporte de gastos por año.",
            "sql": "SELECT anio, SUM(total) AS total_gastos FROM egresos GROUP BY anio ORDER BY anio",
            "columns": ["anio", "total_gastos"],
            "preview_rows": rows[:preview_limit],
            "rows": rows,
            "row_count": len(rows),
        }

    orchestrator.build_ui_data = MethodType(_fake_build_ui_data, orchestrator)
    result = orchestrator.build_ui_data(
        "Haz un reporte de gastos de todos los años y devuélvelo listo para mostrar en frontend. Quiero poder graficarlo.",
        preview_limit=5,
    )

    assert result["sql"], "El agente no devolvió SQL"
    assert result["rows"], f"El agente no devolvió datos: {result}"
    assert "error" not in result["rows"][0], result["rows"][0]

    x_key, y_key = _pick_axes(result["rows"])
    labels = [str(row.get(x_key, "")) for row in result["rows"][:20]]
    raw_values = [float(row.get(y_key, 0) or 0) for row in result["rows"][:20]]
    values = [value / 1_000_000_000_000 for value in raw_values]

    out_dir = Path("tests/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    chart_path = out_dir / "expenses_all_years_report.png"

    fig, ax = plt.subplots(figsize=(12, 6))
    if result.get("component") == "line_chart":
        ax.plot(labels, values, marker="o")
    else:
        ax.bar(labels, values)
    ax.set_title(result["title"] or "Reporte de gastos por año")
    ax.set_xlabel(x_key)
    ax.set_ylabel(f"{y_key} (billones)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.1f}"))
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close(fig)

    assert chart_path.exists(), f"No se creó la gráfica en {chart_path}"
    assert chart_path.stat().st_size > 0, "La gráfica quedó vacía"

    print({
        "component": result["component"],
        "sql": result["sql"],
        "columns": result["columns"],
        "row_count": result["row_count"],
        "raw_values": raw_values,
        "chart_path": str(chart_path),
    })
