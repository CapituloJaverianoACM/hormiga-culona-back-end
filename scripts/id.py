import pandas as pd

# Leer el archivo
df = pd.read_csv("egresos_consolidado.csv")

# Agregar una columna id autoincremental
df.insert(0, "id", range(1, len(df) + 1))

# Guardar el nuevo archivo
df.to_csv("egresos_consolidados_con_id.csv", index=False)

print(f"Archivo generado con {len(df)} registros.")