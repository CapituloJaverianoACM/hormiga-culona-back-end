import argparse
import csv
import glob
import os
import re
from pathlib import Path

PATRON_EGRESOS = "RESUMEN_EGRESOS_PRESUPUESTO_GENERAL_DEL_MUNICIPIO_DE_BUCARAMANGA_*.csv"
PATRON_INGRESOS = "RESUMEN_INGRESOS_PRESUPUESTO_GENERAL_DE_BUCARAMANGA_*.csv"

MAPEO_EGRESOS = [
    None,                        # 0: codigo/rubro crudo, sin documentacion oficial -> se descarta
    "descripcion_rubro",         # 1: tambien es la columna donde aparece el marcador de semestre
    "presupuesto_inicial",       # 2
    "adiciones",                 # 3
    "reducciones",               # 4
    "creditos",                  # 5
    "contracreditos",            # 6
    "presupuesto_definitivo",    # 7
    "disponibilidad_acumulada",  # 8
    "compromiso_acumulado",      # 9
    "obligaciones",              # 10
    "pagos_acumulados",          # 11
    None,                        # 12: siempre vacia/"-88" en todos los periodos revisados -> se descarta
    "saldo_reservas",            # 13
    "pct_ejecucion",             # 14
]

MAPEO_INGRESOS = [
    None,                  # 0: codigo FUT crudo, sin documentacion oficial -> se descarta
    "descripcion",         # 1: tambien es la columna donde aparece el marcador de semestre
    "presupuesto_inicial", # 2
    "adiciones",           # 3
    "reducciones",         # 4
    "creditos",            # 5
    "contracreditos",      # 6
    "presupuesto_final",   # 7
    "recaudos",            # 8
    "recaudo_acumulado",   # 9
    "saldo_por_recaudar",  # 10
    "pct_ejecucion",       # 11
]

CAMPOS_TEXTO = ("descripcion_rubro", "descripcion")

SENTINELAS_VACIO = {
    "-88", "-88.00", "-88,00", "-88.0", "-88,0",
    "-98", "-98.00", "-98,00", "-98.0", "-98,0",
    "-", "--", "", "NA", "NULL", "null",
}
# Si al revisar el log de validacion aparece OTRO numero sospechoso repetido
# identicamente en varias filas de un mismo archivo (ej. -77, -99), agregalo aqui.

# Detecta la fila-marcador de corte semestral sin importar si el archivo es de
# ingresos o egresos, ni el orden dia/mes/anio: "GASTOS A 31 DICIEMBRE 2017",
# "GASTOS A JUNIO 30 DE 2018", "INGRESOS A DICIEMBRE 31 DE 2021", etc.
# Esto evita tener logica distinta para cada tipo de archivo.
RE_MARCADOR_SEMESTRE = re.compile(
    r"\b(?:GASTOS|INGRESOS)\s+A\b.*?\b(JUNIO|DICIEMBRE)\b.*?(\d{4})",
    re.IGNORECASE,
)


def detectar_marcador_semestre(texto):
    """Si el texto es una fila-marcador de corte semestral, retorna (anio, periodo).
    Si no lo es (es una fila de datos normal), retorna None."""
    m = RE_MARCADOR_SEMESTRE.search(texto or "")
    if not m:
        return None
    mes = m.group(1).upper()
    anio = m.group(2)
    periodo = "1" if mes == "JUNIO" else "2"
    return anio, periodo


def detectar_encoding(path):
    with open(path, "rb") as f:
        raw = f.read(20000)
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            raw.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def encontrar_archivo(base_dir, patron):
    candidatos = sorted(glob.glob(os.path.join(str(base_dir), patron)))
    if not candidatos:
        raise FileNotFoundError(
            f"No se encontro ningun archivo que coincida con '{patron}' en {base_dir}."
        )
    # Si hay varias exportaciones (distintas fechas en el nombre), se toma la mas
    # reciente; el sufijo de fecha AAAAMMDD ordena bien alfabeticamente.
    return candidatos[-1]


def limpiar_valor(valor):
    """Convierte texto crudo a numero limpio, o '' si es el centinela de vacio."""
    if valor is None:
        return ""
    v = valor.strip().replace("%", "").strip()
    if v.replace(" ", "") in SENTINELAS_VACIO:
        return ""

    tiene_coma = "," in v
    tiene_punto = "." in v

    try:
        if tiene_coma and tiene_punto:
            if v.rfind(",") > v.rfind("."):
                limpio = v.replace(".", "").replace(",", ".")
            else:
                limpio = v.replace(",", "")
        elif tiene_coma and not tiene_punto:
            partes = v.split(",")
            limpio = v.replace(",", ".") if len(partes[-1]) == 2 else v.replace(",", "")
        elif tiene_punto and not tiene_coma:
            partes = v.split(".")
            limpio = v if len(partes[-1]) == 2 else v.replace(".", "")
        else:
            limpio = v
        return str(float(limpio))
    except ValueError:
        # no era numero (ej. texto libre en descripcion) -> se deja tal cual
        return v


def procesar_archivo(path, mapeo, prefijo_id, log_validacion):
    """Recorre el CSV original completo (todos los semestres pegados uno tras otro),
    detecta los marcadores de semestre y separa la informacion automaticamente,
    sin depender de que el archivo venga pre-segmentado."""
    nombre = os.path.basename(path)
    encoding = detectar_encoding(path)
    ancho_esperado = len(mapeo)

    filas_salida = []
    filas_problema = 0
    filas_basura_saltadas = 0
    resumen_bloques = []  # (anio, periodo, num_filas) para el log

    anio_actual = periodo_actual = None
    bloque_iniciado = False
    en_zona_basura = True
    seq_en_bloque = 0
    filas_del_bloque_actual = 0

    def cerrar_bloque_si_existe():
        if bloque_iniciado:
            resumen_bloques.append((anio_actual, periodo_actual, filas_del_bloque_actual))

    with open(path, "r", encoding=encoding, errors="replace", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not any(c.strip() for c in row):
                continue  # fila totalmente vacia, se ignora

            col_marca = row[1].strip() if len(row) > 1 else ""
            marca = detectar_marcador_semestre(col_marca)
            if marca:
                cerrar_bloque_si_existe()
                anio_actual, periodo_actual = marca
                bloque_iniciado = True
                en_zona_basura = True
                seq_en_bloque = 0
                filas_del_bloque_actual = 0
                continue  # la fila-marcador no es un dato, no se agrega a la salida

            if not bloque_iniciado:
                # Filas antes del primer marcador del archivo (encabezado generico de
                # columnas). No pertenecen a ningun semestre, se descartan.
                continue

            if len(row) < ancho_esperado:
                filas_problema += 1
                row = row + [""] * (ancho_esperado - len(row))
            elif len(row) > ancho_esperado:
                filas_problema += 1
                row = row[:ancho_esperado]

            fila_dict = {}
            for idx, campo in enumerate(mapeo):
                if campo is None:
                    continue  # columna sin valor analitico, se descarta
                valor_crudo = row[idx]
                fila_dict[campo] = valor_crudo.strip() if campo in CAMPOS_TEXTO else limpiar_valor(valor_crudo)

            desc_val = (fila_dict.get("descripcion_rubro") or fila_dict.get("descripcion") or "").strip().upper()
            if en_zona_basura:
                if desc_val in ("", "NO APLICA"):
                    filas_basura_saltadas += 1
                    continue
                en_zona_basura = False

            if desc_val in {"DESCRIPCION RUBRO", "DESCRIPCION", "RUBRO"}:
                filas_basura_saltadas += 1
                continue

            seq_en_bloque += 1
            filas_del_bloque_actual += 1
            fila_dict["id"] = f"{prefijo_id}-{anio_actual}-{periodo_actual}-{len(resumen_bloques) + 1:02d}-{seq_en_bloque:05d}"
            fila_dict["anio"] = anio_actual
            fila_dict["periodo"] = periodo_actual
            fila_dict["archivo_origen"] = nombre
            filas_salida.append(fila_dict)

    cerrar_bloque_si_existe()

    log_validacion.append(f"\n--- {nombre} (encoding={encoding}) ---")
    log_validacion.append(f"  Semestres detectados: {len(resumen_bloques)}")
    for anio, periodo, n in resumen_bloques:
        log_validacion.append(f"    anio={anio} periodo={periodo}: {n} filas de datos")
    log_validacion.append(
        f"  Total filas de datos: {len(filas_salida)}  |  Filas de leyenda descartadas: {filas_basura_saltadas}"
        f"  |  Filas con num. de columnas distinto al esperado: {filas_problema}"
    )
    if not resumen_bloques:
        log_validacion.append(
            "  [ALERTA] No se detecto ningun marcador de semestre en este archivo. "
            "Revisa si cambio el formato del texto del marcador."
        )

    return filas_salida


def consolidar(input_dir, patron_archivo, mapeo, prefijo_id, nombre_salida, log_validacion, output_dir):
    path = encontrar_archivo(input_dir, patron_archivo)
    filas = procesar_archivo(path, mapeo, prefijo_id, log_validacion)

    campos_salida = [c for c in mapeo if c is not None]
    encabezado = ["id", "anio", "periodo"] + campos_salida + ["archivo_origen"]
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    destino = output_path / nombre_salida

    with destino.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=encabezado)
        writer.writeheader()
        writer.writerows(filas)

    log_validacion.append(f"\n>>> {destino.name}: {len(filas)} filas totales, generado desde {os.path.basename(path)}.\n")


def copiar_descripciones(input_dir, output_dir, log_validacion):
    origen = Path(input_dir) / "data_base_descriptions.csv"
    if not origen.exists():
        return None
    destino = Path(output_dir) / "data_base_descriptions.csv"
    destino.write_text(origen.read_text(encoding="utf-8"), encoding="utf-8")
    log_validacion.append(f"\n>>> {destino.name}: copiado desde {origen.name}.\n")
    return destino


def run_processing(input_dir=".", output_dir="."):
    log_validacion = []

    log_validacion.append("=" * 70)
    log_validacion.append("EGRESOS")
    log_validacion.append("=" * 70)
    consolidar(input_dir, PATRON_EGRESOS, MAPEO_EGRESOS, "egr", "egresos_consolidado.csv", log_validacion, output_dir)

    log_validacion.append("=" * 70)
    log_validacion.append("INGRESOS")
    log_validacion.append("=" * 70)
    consolidar(input_dir, PATRON_INGRESOS, MAPEO_INGRESOS, "ing", "ingresos_consolidado.csv", log_validacion, output_dir)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    descriptions = copiar_descripciones(input_dir, output_dir, log_validacion)
    salida = "\n".join(log_validacion)
    validacion = output_path / "validacion_consolidacion.txt"
    validacion.write_text(salida, encoding="utf-8")

    print(salida)
    print("\n[OK] Generados: egresos_consolidado.csv, ingresos_consolidado.csv, validacion_consolidacion.txt")
    return {
        "egresos": str(output_path / "egresos_consolidado.csv"),
        "ingresos": str(output_path / "ingresos_consolidado.csv"),
        "validacion": str(validacion),
        "descriptions": str(descriptions) if descriptions else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Consolida los CSV de ingresos y egresos")
    parser.add_argument("--input-dir", default=".", help="Directorio donde estan los CSV crudos")
    parser.add_argument("--output-dir", default=".", help="Directorio donde se escriben los CSV consolidados")
    args = parser.parse_args()
    run_processing(input_dir=args.input_dir, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
