import os
import csv
import re
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from data_processing import (
    PATRON_EGRESOS, PATRON_INGRESOS,
    MAPEO_EGRESOS, MAPEO_INGRESOS,
    CAMPOS_TEXTO, SENTINELAS_VACIO,
    detectar_marcador_semestre, detectar_encoding, encontrar_archivo,
)

OUT_DIR = "eda_output"


def _to_float_o_none(v):
    """Intento simple de parseo numerico solo para fines estadisticos del EDA
    (no reemplaza limpiar_valor(), que es la logica oficial de limpieza)."""
    v = (v or "").strip().replace("%", "")
    if v.replace(" ", "") in SENTINELAS_VACIO:
        return None
    v2 = v.replace(".", "").replace(",", ".") if v.count(",") == 1 and v.count(".") >= 1 else v.replace(",", ".")
    try:
        return float(v2)
    except ValueError:
        return None


def analizar_archivo(patron, mapeo, nombre_dataset, reporte):
    path = encontrar_archivo(patron)
    encoding = detectar_encoding(path)
    ancho_esperado = len(mapeo)
    nombres_col = [c if c else f"col_{i}_descartada" for i, c in enumerate(mapeo)]

    total_filas = 0
    filas_vacias = 0
    marcadores_encontrados = []
    anchos = Counter()
    valores_centinela_por_col = defaultdict(Counter)
    valores_numericos_por_col = defaultdict(list)

    with open(path, "r", encoding=encoding, errors="replace", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not any(c.strip() for c in row):
                filas_vacias += 1
                continue
            total_filas += 1
            anchos[len(row)] += 1

            col_marca = row[1].strip() if len(row) > 1 else ""
            marca = detectar_marcador_semestre(col_marca)
            if marca:
                marcadores_encontrados.append(marca)
                continue

            for idx, campo in enumerate(mapeo):
                if campo is None or idx >= len(row):
                    continue
                valor = row[idx].strip()
                if campo in CAMPOS_TEXTO:
                    continue
                if valor.replace(" ", "") in SENTINELAS_VACIO:
                    valores_centinela_por_col[campo][valor if valor else "(vacio)"] += 1
                else:
                    num = _to_float_o_none(valor)
                    if num is not None:
                        valores_numericos_por_col[campo].append(num)

    # ---- Grafica 1: % de valores centinela (candidatos a nulo) por columna ----
    cols = [c for c in mapeo if c is not None and c not in CAMPOS_TEXTO]
    porcentajes = []
    for c in cols:
        n_centinela = sum(valores_centinela_por_col[c].values())
        n_total = n_centinela + len(valores_numericos_por_col[c])
        porcentajes.append(100 * n_centinela / n_total if n_total else 0)

    plt.figure(figsize=(10, 5))
    plt.bar(cols, porcentajes, color="#4C72B0")
    plt.ylabel("% de valores centinela (-88, -98, vacio, etc.)")
    plt.title(f"{nombre_dataset}: prevalencia de valores centinela por columna")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, f"{nombre_dataset}_centinelas_por_columna.png"), dpi=130)
    plt.close()

    # ---- Grafica 2: boxplots de columnas numericas (para ver "datos borde"/outliers) ----
    plt.figure(figsize=(10, 5))
    datos_box = [valores_numericos_por_col[c] for c in cols if valores_numericos_por_col[c]]
    etiquetas_box = [c for c in cols if valores_numericos_por_col[c]]
    if datos_box:
        plt.boxplot(datos_box, labels=etiquetas_box, showfliers=True)
        plt.yscale("symlog")  # las cifras de presupuesto tienen escalas muy distintas
        plt.title(f"{nombre_dataset}: distribucion y outliers por columna (escala simlog)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, f"{nombre_dataset}_outliers_boxplot.png"), dpi=130)
    plt.close()

    # ---- Grafica 3: distribucion de anchos de fila (justifica el padding/truncado) ----
    plt.figure(figsize=(6, 4))
    anchos_ordenados = sorted(anchos.items())
    plt.bar([str(a) for a, _ in anchos_ordenados], [n for _, n in anchos_ordenados], color="#DD8452")
    plt.axvline(x=str(ancho_esperado), color="green", linestyle="--", label=f"ancho esperado ({ancho_esperado})")
    plt.ylabel("numero de filas")
    plt.xlabel("numero de columnas en la fila")
    plt.title(f"{nombre_dataset}: irregularidad en el ancho de las filas")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, f"{nombre_dataset}_anchos_de_fila.png"), dpi=130)
    plt.close()

    # ---- Reporte de texto ----
    reporte.append(f"\n{'=' * 70}\n{nombre_dataset.upper()}  ({os.path.basename(path)}, encoding={encoding})\n{'=' * 70}")
    reporte.append(f"Total filas leidas: {total_filas}  |  Filas totalmente vacias: {filas_vacias}")
    reporte.append(f"Marcadores de semestre detectados: {len(marcadores_encontrados)} -> {marcadores_encontrados}")
    reporte.append(f"Distribucion de anchos de fila: {dict(sorted(anchos.items()))} (esperado={ancho_esperado})")
    reporte.append("\nPrevalencia de valores centinela por columna:")
    for c, pct in zip(cols, porcentajes):
        valores_vistos = dict(valores_centinela_por_col[c])
        reporte.append(f"  - {c}: {pct:.1f}% centinela  |  valores vistos: {valores_vistos}")
    reporte.append("\nEstadisticos de columnas numericas (sin centinelas):")
    for c in cols:
        vals = valores_numericos_por_col[c]
        if not vals:
            continue
        vals_ordenados = sorted(vals)
        n = len(vals_ordenados)
        mediana = vals_ordenados[n // 2]
        reporte.append(
            f"  - {c}: n={n}  min={min(vals):,.0f}  max={max(vals):,.0f}  "
            f"mediana={mediana:,.0f}  promedio={sum(vals)/n:,.0f}"
        )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    reporte = ["REPORTE EDA - datos crudos ANTES de la limpieza",
               "Este reporte es la evidencia de las decisiones documentadas en decisiones_limpieza.md\n"]

    analizar_archivo(PATRON_EGRESOS, MAPEO_EGRESOS, "egresos", reporte)
    analizar_archivo(PATRON_INGRESOS, MAPEO_INGRESOS, "ingresos", reporte)

    texto = "\n".join(reporte)
    with open(os.path.join(OUT_DIR, "reporte_eda.txt"), "w", encoding="utf-8") as f:
        f.write(texto)

    print(texto)
    print(f"\n[OK] Graficas y reporte guardados en ./{OUT_DIR}/")


if __name__ == "__main__":
    main()
