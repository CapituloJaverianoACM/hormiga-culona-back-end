from decimal import Decimal
from pathlib import Path

import matplotlib.pyplot as plt
from dotenv import load_dotenv
from matplotlib.ticker import FuncFormatter

from services.orchestrator import AgentOrchestratorService
from services.schema import SchemaCacheService


load_dotenv()


"""
Made with AI for visualizing the output of the UI Agent. 
It runs a test query and generates a chart from the results.
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
    schema_service = SchemaCacheService()
    schema_service.refresh_schema_sync()

    orchestrator = AgentOrchestratorService()
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
