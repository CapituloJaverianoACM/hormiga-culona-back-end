import os
import csv
import glob
import chardet
from collections import defaultdict

BASE_DIR = "."  # ajusta si corres el script desde otro lugar
CARPETAS = ["Egresos", "Ingresos"]
MUESTRA_FILAS = 500  # cuantas filas leer para inferir tipos/nulos (no todo el archivo)

def detectar_encoding_y_sep(path):
    with open(path, "rb") as f:
        raw = f.read(20000)  # solo primeros ~20kb, no todo el archivo
    enc_guess = chardet.detect(raw)
    encoding = enc_guess["encoding"] or "utf-8"
    confianza = enc_guess["confidence"]

    # detectar separador probando los mas comunes en la primera linea
    try:
        texto = raw.decode(encoding, errors="replace")
    except Exception:
        texto = raw.decode("utf-8", errors="replace")
        encoding = "utf-8 (fallback)"

    primera_linea = texto.split("\n")[0]
    candidatos = [",", ";", "\t", "|"]
    sep = max(candidatos, key=lambda c: primera_linea.count(c))
    return encoding, confianza, sep

def inferir_tipo(valores):
    """Infiere tipo dominante de una lista de valores (strings) ignorando vacios."""
    valores = [v for v in valores if v not in (None, "", "NA", "NULL", "null")]
    if not valores:
        return "vacio/desconocido"

    n = len(valores)
    n_num = 0
    n_fecha = 0
    for v in valores:
        v2 = v.replace(".", "", 1).replace(",", "", 1).replace("-", "", 1)
        if v2.isdigit():
            n_num += 1
        if any(c in v for c in ["/", "-"]) and any(c.isdigit() for c in v) and len(v) <= 12:
            n_fecha += 1

    if n_num / n > 0.8:
        return "numerico"
    if n_fecha / n > 0.6:
        return "posible fecha"
    return "texto"

def analizar_archivo(path):
    info = {"archivo": os.path.basename(path)}
    encoding, confianza, sep = detectar_encoding_y_sep(path)
    info["encoding"] = f"{encoding} (confianza {confianza:.2f})"
    info["separador"] = repr(sep)

    filas_muestra = []
    total_filas = 0
    columnas = []
    try:
        with open(path, "r", encoding=encoding, errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=sep)
            for i, row in enumerate(reader):
                if i == 0:
                    columnas = row
                    continue
                total_filas += 1
                if len(filas_muestra) < MUESTRA_FILAS:
                    filas_muestra.append(row)
    except Exception as e:
        info["error"] = str(e)
        return info

    info["n_columnas"] = len(columnas)
    info["columnas"] = columnas
    info["total_filas_aprox"] = total_filas  # exacto, ya que iteramos todo el archivo (liviano, solo texto)

    # nulos y tipo por columna, usando solo la muestra
    nulos_por_col = defaultdict(int)
    valores_por_col = defaultdict(list)
    for row in filas_muestra:
        for idx, col in enumerate(columnas):
            val = row[idx].strip() if idx < len(row) else ""
            valores_por_col[col].append(val)
            if val in ("", "NA", "NULL", "null"):
                nulos_por_col[col] += 1

    detalle_columnas = {}
    for col in columnas:
        vals = valores_por_col[col]
        ejemplo = next((v for v in vals if v not in ("", "NA", "NULL", "null")), "")
        detalle_columnas[col] = {
            "tipo_inferido": inferir_tipo(vals),
            "nulos_en_muestra": f"{nulos_por_col[col]}/{len(vals)}",
            "ejemplo": ejemplo[:40]
        }
    info["detalle_columnas"] = detalle_columnas
    return info

def main():
    reporte = []
    for carpeta in CARPETAS:
        ruta_carpeta = os.path.join(BASE_DIR, carpeta)
        archivos = sorted(glob.glob(os.path.join(ruta_carpeta, "*.csv")))
        if not archivos:
            reporte.append(f"\n[!] No se encontraron CSVs en {ruta_carpeta}\n")
            continue

        reporte.append(f"\n{'='*70}\nCARPETA: {carpeta}  ({len(archivos)} archivos)\n{'='*70}")

        esquemas = {}  # nombre_archivo -> tupla de columnas
        detalles_todos = []

        for path in archivos:
            info = analizar_archivo(path)
            detalles_todos.append(info)
            if "error" in info:
                reporte.append(f"\n--- {info['archivo']} ---\n  ERROR leyendo archivo: {info['error']}")
                continue
            esquemas[info["archivo"]] = tuple(info["columnas"])

        # comparar esquemas entre archivos de la carpeta
        esquemas_unicos = set(esquemas.values())
        reporte.append(f"\n>> Numero de esquemas distintos de columnas encontrados: {len(esquemas_unicos)}")
        if len(esquemas_unicos) > 1:
            reporte.append(">> ATENCION: el esquema de columnas CAMBIA entre archivos. Detalle:")
            grupos = defaultdict(list)
            for archivo, esquema in esquemas.items():
                grupos[esquema].append(archivo)
            for i, (esquema, archivos_grupo) in enumerate(grupos.items(), 1):
                reporte.append(f"\n  Esquema #{i} (usado por: {', '.join(archivos_grupo)}):")
                reporte.append(f"    Columnas: {list(esquema)}")
        else:
            reporte.append(">> Todos los archivos comparten el mismo esquema de columnas. Bien.")
            if esquemas:
                reporte.append(f"   Columnas: {list(next(iter(esquemas_unicos)))}")

        # detalle por archivo
        for info in detalles_todos:
            if "error" in info:
                continue
            reporte.append(f"\n--- {info['archivo']} ---")
            reporte.append(f"  Encoding: {info['encoding']}")
            reporte.append(f"  Separador: {info['separador']}")
            reporte.append(f"  Columnas ({info['n_columnas']}): {info['columnas']}")
            reporte.append(f"  Filas totales: {info['total_filas_aprox']}")
            reporte.append(f"  Detalle por columna (basado en muestra de hasta {MUESTRA_FILAS} filas):")
            for col, det in info["detalle_columnas"].items():
                reporte.append(
                    f"    - {col}: tipo={det['tipo_inferido']}, "
                    f"nulos_muestra={det['nulos_en_muestra']}, ejemplo='{det['ejemplo']}'"
                )

    salida = "\n".join(reporte)
    with open("reporte_estructura.txt", "w", encoding="utf-8") as f:
        f.write(salida)

    print(salida)
    print("\n\n[OK] Reporte guardado en reporte_estructura.txt")

if __name__ == "__main__":
    main()
