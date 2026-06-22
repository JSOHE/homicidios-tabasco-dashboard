# ============================================================
# PROYECTO: Homicidios en Tabasco con datos del SESNSP
# SCRIPT 03: Calcular víctimas por municipio y mes
#
# OBJETIVO:
#   Obtener una tabla municipal mensual con:
#   1. Víctimas de homicidio doloso
#   2. Víctimas de feminicidio
#   3. Total de muertes intencionales:
#      homicidio doloso + feminicidio
# ============================================================


from pathlib import Path
import pandas as pd
from config_actualizacion import detectar_meses_disponibles, seleccionar_csv_municipal_mas_reciente


# ------------------------------------------------------------
# 1. Rutas del proyecto
# ------------------------------------------------------------

BASE_DIR = Path("/Users/soto/homicidios_tabasco")

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TABLES_DIR = BASE_DIR / "outputs" / "tables"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 2. Meses que vienen como columnas en la base original
# ------------------------------------------------------------

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

ORDEN_MESES = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12
}


# ------------------------------------------------------------
# 3. Leer archivo
# ------------------------------------------------------------

archivo_datos = seleccionar_csv_municipal_mas_reciente(
    RAW_DIR,
    anio=2026,
)

print("Archivo que voy a leer:")
print(archivo_datos)

df = pd.read_csv(archivo_datos, encoding="latin-1")

meses_disponibles = detectar_meses_disponibles(df)
print("\nMeses disponibles detectados:")
print(meses_disponibles)


# ------------------------------------------------------------
# 4. Filtrar solo Tabasco
# ------------------------------------------------------------

tabasco = df[df["Entidad"] == "Tabasco"].copy()

print("\nFilas de Tabasco antes de transformar:")
print(tabasco.shape)


# ------------------------------------------------------------
# 5. Convertir de formato ancho a formato largo
# ------------------------------------------------------------

# La base original tiene una columna por mes:
# Enero, Febrero, Marzo, Abril...
#
# Para analizar mejor, queremos una sola columna llamada "Mes"
# y otra columna llamada "Victimas".
#
# pd.melt hace precisamente eso.

columnas_identificacion = [
    "Año",
    "Clave_Ent",
    "Entidad",
    "Cve. Municipio",
    "Municipio",
    "Bien jurídico afectado",
    "Tipo de delito",
    "Subtipo de delito",
    "Modalidad",
    "Sexo",
    "Rango de edad"
]

tabasco_largo = tabasco.melt(
    id_vars=columnas_identificacion,
    value_vars=meses_disponibles,
    var_name="Mes",
    value_name="Victimas"
)

print("\nFilas de Tabasco después de pasar a formato largo:")
print(tabasco_largo.shape)


# ------------------------------------------------------------
# 6. Limpiar la columna de víctimas
# ------------------------------------------------------------

# Algunos meses pueden venir vacíos porque todavía no hay datos.
# Por ejemplo, si el corte es abril 2026, mayo-diciembre vienen vacíos.
#
# Convertimos Victimas a número.
# Si hay valores vacíos, los convertimos en 0.

tabasco_largo["Victimas"] = pd.to_numeric(
    tabasco_largo["Victimas"],
    errors="coerce"
).fillna(0)


# Agregamos número de mes para ordenar correctamente.
tabasco_largo["Mes_num"] = tabasco_largo["Mes"].map(ORDEN_MESES)


# ------------------------------------------------------------
# 7. Filtrar solo meses con datos
# ------------------------------------------------------------

# Los meses se detectan automáticamente desde el CSV seleccionado.


# ------------------------------------------------------------
# 8. Crear filtros de homicidio doloso y feminicidio
# ------------------------------------------------------------

# Filtro para homicidio doloso:
# Tipo de delito debe ser Homicidio
# y Subtipo de delito debe contener la palabra Doloso.
filtro_homicidio_doloso = (
    tabasco_largo["Tipo de delito"].str.contains("Homicidio", case=False, na=False)
    &
    tabasco_largo["Subtipo de delito"].str.contains("Doloso", case=False, na=False)
)

# Filtro para feminicidio:
# Tipo de delito debe ser Feminicidio.
filtro_feminicidio = (
    tabasco_largo["Tipo de delito"].str.contains("Feminicidio", case=False, na=False)
)

# Conservamos solo las filas que sean homicidio doloso o feminicidio.
letal_intencional = tabasco_largo[
    filtro_homicidio_doloso | filtro_feminicidio
].copy()


# ------------------------------------------------------------
# 9. Crear una categoría clara para el análisis
# ------------------------------------------------------------

# En vez de trabajar con textos largos,
# creamos una columna sencilla llamada categoria_analisis.

letal_intencional["categoria_analisis"] = "otro"

letal_intencional.loc[
    filtro_homicidio_doloso,
    "categoria_analisis"
] = "homicidio_doloso"

letal_intencional.loc[
    filtro_feminicidio,
    "categoria_analisis"
] = "feminicidio"


# ------------------------------------------------------------
# 10. Agrupar por municipio, mes y categoría
# ------------------------------------------------------------

municipal_largo = (
    letal_intencional
    .groupby(
        [
            "Año",
            "Entidad",
            "Cve. Municipio",
            "Municipio",
            "Mes_num",
            "Mes",
            "categoria_analisis"
        ],
        as_index=False
    )["Victimas"]
    .sum()
)


# ------------------------------------------------------------
# 11. Pasar categorías a columnas
# ------------------------------------------------------------

# Queremos que homicidio_doloso y feminicidio sean columnas separadas.
# Para eso usamos pivot_table.

municipal = municipal_largo.pivot_table(
    index=[
        "Año",
        "Entidad",
        "Cve. Municipio",
        "Municipio",
        "Mes_num",
        "Mes"
    ],
    columns="categoria_analisis",
    values="Victimas",
    aggfunc="sum",
    fill_value=0
).reset_index()


# Quitamos el nombre automático que deja pandas en las columnas.
municipal.columns.name = None


# ------------------------------------------------------------
# 12. Asegurar que existan las columnas esperadas
# ------------------------------------------------------------

# Puede pasar que en algún corte no haya feminicidios,
# y entonces pandas no cree esa columna.
# Para evitar errores, la creamos en cero si no existe.

if "homicidio_doloso" not in municipal.columns:
    municipal["homicidio_doloso"] = 0

if "feminicidio" not in municipal.columns:
    municipal["feminicidio"] = 0


# ------------------------------------------------------------
# 13. Crear total intencional
# ------------------------------------------------------------

municipal["total_intencional"] = (
    municipal["homicidio_doloso"] + municipal["feminicidio"]
)


# ------------------------------------------------------------
# 14. Ordenar resultados
# ------------------------------------------------------------

municipal = municipal.sort_values(
    ["Municipio", "Mes_num"]
).reset_index(drop=True)


# ------------------------------------------------------------
# 15. Guardar resultado
# ------------------------------------------------------------

salida = TABLES_DIR / "tabasco_municipal_homicidio_feminicidio_2026_actual.csv"

municipal.to_csv(salida, index=False, encoding="utf-8-sig")

print("\nTabla municipal generada correctamente:")
print(salida)

print("\nPrimeras filas de la tabla final:")
print(municipal.head(20).to_string(index=False))


# ------------------------------------------------------------
# 16. Crear resumen estatal desde la tabla municipal
# ------------------------------------------------------------

estatal = (
    municipal
    .groupby(["Año", "Entidad", "Mes_num", "Mes"], as_index=False)
    [
        ["homicidio_doloso", "feminicidio", "total_intencional"]
    ]
    .sum()
    .sort_values("Mes_num")
)

salida_estatal = TABLES_DIR / "tabasco_estatal_homicidio_feminicidio_2026_actual.csv"

estatal.to_csv(salida_estatal, index=False, encoding="utf-8-sig")

print("\nResumen estatal:")
print(estatal.to_string(index=False))

print("\nResumen estatal guardado en:")
print(salida_estatal)