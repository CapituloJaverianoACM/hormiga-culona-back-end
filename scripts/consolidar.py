import os
import csv
import glob
import re
import chardet

BASE_DIR = "."

CAMPOS_EGRESOS = [
    "codigo_rubro", "descripcion_rubro", "presupuesto_inicial", "adiciones",
    "reducciones", "creditos", "contracreditos", "presupuesto_definitivo",
    "disponibilidad_acumulada", "compromiso_acumulado", "obligaciones",
    "pagos_acumulados", "extra_1", "saldo_reservas", "pct_ejecucion",
]

CAMPOS_INGRESOS = [
    "codigo_fut", "descripcion", "presupuesto_inicial", "adiciones",
    "reducciones", "creditos", "contracreditos", "presupuesto_final",
    "recaudos", "recaudo_acumulado", "saldo_por_recaudar", "pct_ejecucion",
]

SENTINELAS_VACIO = {
    "-88", "-88.00", "-88,00", "-88.0", "-88,0",
    "-98", "-98.00", "-98,00", "-98.0", "-98,0",
    "-", "--", "", "NA", "NULL", "null",
}
# Si al revisar el log de validacion aparece OTRO numero sospechoso repetido
# identicamente en varias filas de un mismo archivo (ej. -77, -99), agregalo aqui.


def detectar_encoding(path):
    with open(path, "rb") as f:
        raw = f.read(20000)
    guess = chardet.detect(raw)
    return guess["encoding"] or "utf-8"


def extraer_anio_periodo(nombre_archivo):
    m = re.search(r"(\d{4})_(\d{2})", nombre_archivo)
    if not m:
        return "", ""
    anio, periodo_raw = m.group(1), m.group(2)
    periodo = "1" if periodo_raw == "01" else "2"
    return anio, periodo


def normalizar_codigo(codigo):
    """Quita espacios y puntos para que el mismo codigo jerarquico sea comparable
    entre anios, sin importar si el archivo original lo escribio '2 1 1', '211' o '2.1.1'."""
    return re.sub(r"[\s.]", "", codigo or "")


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


def procesar_archivo(path, campos_destino, log_validacion):
    nombre = os.path.basename(path)
    anio, periodo = extraer_anio_periodo(nombre)
    encoding = detectar_encoding(path)

    filas_salida = []
    filas_problema = 0
    filas_basura_saltadas = 0
    muestra_log = []
    en_zona_basura = True  # seguimos "en la cabecera" hasta ver la primera fila con datos reales

    campos_texto = ("codigo_rubro", "codigo_fut", "descripcion_rubro", "descripcion")

    with open(path, "r", encoding=encoding, errors="replace", newline="") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0:
                continue  # fila 0 = encabezado con nombres de columna, siempre se salta
            if nombre == "Egresos_2017_02.csv" and i == 1:
                # Egresos_2017_02 tiene una fila extra de sub-etiqueta (caso especial,
                # confirmado en validacion) antes de la fila de leyenda
                continue
            if not any(c.strip() for c in row):
                continue  # fila totalmente vacia, se ignora

            fila_dict = {"anio": anio, "periodo": periodo}
            if len(row) < len(campos_destino):
                filas_problema += 1
                row = row + [""] * (len(campos_destino) - len(row))
            elif len(row) > len(campos_destino):
                filas_problema += 1
                row = row[: len(campos_destino)]

            for idx, campo in enumerate(campos_destino):
                valor_crudo = row[idx]
                if campo in campos_texto:
                    fila_dict[campo] = valor_crudo.strip()
                else:
                    fila_dict[campo] = limpiar_valor(valor_crudo)

            if "codigo_rubro" in fila_dict:
                fila_dict["codigo_rubro_normalizado"] = normalizar_codigo(fila_dict["codigo_rubro"])
            elif "codigo_fut" in fila_dict:
                fila_dict["codigo_fut_normalizado"] = normalizar_codigo(fila_dict["codigo_fut"])

            if en_zona_basura:
                desc_val = (fila_dict.get("descripcion_rubro") or fila_dict.get("descripcion") or "").strip().upper()
                if desc_val in ("", "NO APLICA"):
                    filas_basura_saltadas += 1
                    continue  # sigue siendo fila de leyenda/relleno, descartar
                en_zona_basura = False  # esta ya es la primera fila real (aunque venga con -88 en los montos, es legitima)

            fila_dict["archivo_origen"] = nombre
            filas_salida.append(fila_dict)

            if len(muestra_log) < 3:
                muestra_log.append(fila_dict.copy())

    log_validacion.append(f"\n--- {nombre} (encoding={encoding}) ---")
    log_validacion.append(
        f"  Filas de datos: {len(filas_salida)}  |  Filas basura descartadas al inicio: {filas_basura_saltadas}"
        f"  |  Filas con num. de columnas distinto al esperado: {filas_problema}"
    )
    log_validacion.append("  Primeras 3 filas limpias:")
    for fila in muestra_log:
        log_validacion.append(f"    {fila}")

    return filas_salida


def consolidar(carpeta, campos_destino, nombre_salida, log_validacion):
    archivos = sorted(glob.glob(os.path.join(BASE_DIR, carpeta, "*.csv")))
    todas_las_filas = []
    for path in archivos:
        todas_las_filas.extend(procesar_archivo(path, campos_destino, log_validacion))

    codigo_campo = campos_destino[0]  # 'codigo_rubro' o 'codigo_fut'
    campos_con_normalizado = [codigo_campo, f"{codigo_campo}_normalizado"] + campos_destino[1:]
    encabezado = ["anio", "periodo"] + campos_con_normalizado + ["archivo_origen"]
    with open(nombre_salida, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=encabezado)
        writer.writeheader()
        writer.writerows(todas_las_filas)

    log_validacion.append(f"\n>>> {nombre_salida}: {len(todas_las_filas)} filas totales, {len(archivos)} archivos consolidados.\n")


def main():
    log_validacion = []

    log_validacion.append("=" * 70)
    log_validacion.append("EGRESOS")
    log_validacion.append("=" * 70)
    consolidar("Egresos", CAMPOS_EGRESOS, "egresos_consolidado.csv", log_validacion)

    log_validacion.append("=" * 70)
    log_validacion.append("INGRESOS")
    log_validacion.append("=" * 70)
    consolidar("Ingresos", CAMPOS_INGRESOS, "ingresos_consolidado.csv", log_validacion)

    salida = "\n".join(log_validacion)
    with open("validacion_consolidacion.txt", "w", encoding="utf-8") as f:
        f.write(salida)

    print(salida)
    print("\n[OK] Generados: egresos_consolidado.csv, ingresos_consolidado.csv, validacion_consolidacion.txt")


if __name__ == "__main__":
    main()