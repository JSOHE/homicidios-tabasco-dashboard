# ============================================================
# PROYECTO: Homicidios en Tabasco con datos del SESNSP/RNID
# SCRIPT 03: Preparar tablas analíticas para Tabasco
#
# OBJETIVO:
#   Este script limpia y transforma la base municipal de víctimas 2026
#   para construir tablas listas para análisis y visualización.
#
#   Separa:
#   1. Homicidio doloso consumado
#   2. Homicidio culposo consumado
#   3. Feminicidio consumado
#   4. Tentativa de homicidio doloso
#   5. Tentativa de feminicidio
#
#   También crea indicadores:
#   - total_intencional =
#       homicidio_doloso + feminicidio
#
#   - total_homicidios_y_feminicidio =
#       homicidio_doloso + homicidio_culposo + feminicidio
#
#   - promedio_diario_total_homicidios =
#       total_homicidios_y_feminicidio / días del mes
#
# ENTRADA:
#   data/raw/RNID-Victimas_Municipal-2026-may2026.csv
#
# SALIDAS:
#   outputs/tables/analiticas/
# ============================================================


# ------------------------------------------------------------
# 1. Importar librerías
# ------------------------------------------------------------

from pathlib import Path
import unicodedata
import re
import calendar

import pandas as pd
from config_actualizacion import seleccionar_csv_municipal_mas_reciente


# ------------------------------------------------------------
# 2. Definir rutas del proyecto
# ------------------------------------------------------------

BASE_DIR = Path("/Users/soto/homicidios_tabasco")

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TABLES_DIR = BASE_DIR / "outputs" / "tables"
ANALYTIC_DIR = TABLES_DIR / "analiticas"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)
ANALYTIC_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 3. Definir meses
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
# 4. Funciones auxiliares
# ------------------------------------------------------------

def normalizar_texto(valor):
    """
    Convierte un texto a una versión más fácil de comparar:
    - minúsculas
    - sin acentos
    - sin espacios dobles

    Ejemplo:
    'Homicidio Doloso' -> 'homicidio doloso'
    """
    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto)
    return texto


def leer_csv_robusto(ruta_csv):
    """
    Intenta leer el CSV con varias codificaciones.
    Esto es útil porque algunos archivos oficiales traen acentos o ñ
    en codificaciones distintas a UTF-8.
    """
    codificaciones = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    for encoding in codificaciones:
        try:
            print(f"Intentando leer con encoding: {encoding}")
            df = pd.read_csv(ruta_csv, encoding=encoding)
            print(f"Archivo leído correctamente con encoding: {encoding}")
            return df
        except UnicodeDecodeError:
            print(f"No funcionó con encoding: {encoding}")

    raise ValueError("No pude leer el archivo con las codificaciones probadas.")


def guardar_csv(df, ruta):
    """
    Guarda una tabla en CSV usando utf-8-sig.
    Este encoding ayuda a que Excel abra bien acentos y ñ.
    """
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    print(f"Tabla guardada: {ruta}")


def porcentaje_seguro(numerador, denominador):
    """
    Calcula porcentaje evitando división entre cero.
    """
    if denominador == 0:
        return 0
    return numerador / denominador * 100


# ------------------------------------------------------------
# 5. Buscar archivo CSV en data/raw
# ------------------------------------------------------------

archivo_datos = seleccionar_csv_municipal_mas_reciente(
    RAW_DIR,
    anio=2026,
)

print("\nArchivo seleccionado:")
print(archivo_datos)


# ------------------------------------------------------------
# 6. Leer base original
# ------------------------------------------------------------

df = leer_csv_robusto(archivo_datos)

print("\nDimensiones de la base original:")
print(df.shape)

print("\nColumnas:")
print(df.columns.tolist())


# ------------------------------------------------------------
# 7. Detectar meses disponibles
# ------------------------------------------------------------

# El archivo más reciente se selecciona automáticamente.
# También se detectan automáticamente los meses con datos.
# Esta parte detecta automáticamente qué meses tienen algún dato no vacío.

meses_disponibles = []

for mes in MESES:
    if mes in df.columns:
        if df[mes].notna().any():
            meses_disponibles.append(mes)

print("\nMeses disponibles detectados:")
print(meses_disponibles)

if len(meses_disponibles) == 0:
    raise ValueError("No detecté meses con datos en el archivo.")


# ------------------------------------------------------------
# 8. Filtrar Tabasco
# ------------------------------------------------------------

df["_entidad_norm"] = df["Entidad"].apply(normalizar_texto)

tabasco = df[df["_entidad_norm"] == "tabasco"].copy()

print("\nFilas de Tabasco:")
print(tabasco.shape)

if tabasco.empty:
    raise ValueError("No encontré registros para Tabasco.")


# ------------------------------------------------------------
# 9. Convertir de formato ancho a formato largo
# ------------------------------------------------------------

# La base original tiene columnas Enero, Febrero, Marzo, Abril...
# Para analizar, necesitamos una columna Mes y una columna Victimas.

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

tabasco_largo["Victimas"] = pd.to_numeric(
    tabasco_largo["Victimas"],
    errors="coerce"
).fillna(0)

tabasco_largo["Mes_num"] = tabasco_largo["Mes"].map(ORDEN_MESES)

print("\nBase Tabasco en formato largo:")
print(tabasco_largo.shape)


# ------------------------------------------------------------
# 10. Normalizar campos de clasificación
# ------------------------------------------------------------

tabasco_largo["_tipo_norm"] = tabasco_largo["Tipo de delito"].apply(normalizar_texto)
tabasco_largo["_subtipo_norm"] = tabasco_largo["Subtipo de delito"].apply(normalizar_texto)
tabasco_largo["_modalidad_norm"] = tabasco_largo["Modalidad"].apply(normalizar_texto)


# ------------------------------------------------------------
# 11. Clasificar eventos
# ------------------------------------------------------------

# Creamos una nueva columna llamada categoria_analisis.
# Esta nos permitirá separar delitos consumados de tentativas.

tabasco_largo["categoria_analisis"] = "otro"
tabasco_largo["tipo_evento"] = "otro"

# Homicidio doloso consumado
mask_homicidio_doloso = (
    (tabasco_largo["_tipo_norm"] == "homicidio")
    &
    (tabasco_largo["_subtipo_norm"] == "homicidio doloso")
)

# Homicidio culposo consumado
mask_homicidio_culposo = (
    (tabasco_largo["_tipo_norm"] == "homicidio")
    &
    (tabasco_largo["_subtipo_norm"] == "homicidio culposo")
)

# Feminicidio consumado
mask_feminicidio = (
    (tabasco_largo["_tipo_norm"] == "feminicidio")
    &
    (tabasco_largo["_subtipo_norm"] == "feminicidio")
)

# Tentativa de homicidio doloso
mask_tentativa_homicidio = (
    (tabasco_largo["_tipo_norm"] == "homicidio")
    &
    (tabasco_largo["_subtipo_norm"] == "tentativa de homicidio doloso")
)

# Tentativa de feminicidio
mask_tentativa_feminicidio = (
    (tabasco_largo["_tipo_norm"] == "feminicidio")
    &
    (tabasco_largo["_subtipo_norm"] == "tentativa de feminicidio")
)

tabasco_largo.loc[mask_homicidio_doloso, "categoria_analisis"] = "homicidio_doloso"
tabasco_largo.loc[mask_homicidio_culposo, "categoria_analisis"] = "homicidio_culposo"
tabasco_largo.loc[mask_feminicidio, "categoria_analisis"] = "feminicidio"
tabasco_largo.loc[mask_tentativa_homicidio, "categoria_analisis"] = "tentativa_homicidio_doloso"
tabasco_largo.loc[mask_tentativa_feminicidio, "categoria_analisis"] = "tentativa_feminicidio"

tabasco_largo.loc[
    mask_homicidio_doloso | mask_homicidio_culposo | mask_feminicidio,
    "tipo_evento"
] = "consumado"

tabasco_largo.loc[
    mask_tentativa_homicidio | mask_tentativa_feminicidio,
    "tipo_evento"
] = "tentativa"


# ------------------------------------------------------------
# 12. Crear bases de trabajo
# ------------------------------------------------------------

base_letal = tabasco_largo[
    tabasco_largo["categoria_analisis"].isin(
        [
            "homicidio_doloso",
            "homicidio_culposo",
            "feminicidio",
            "tentativa_homicidio_doloso",
            "tentativa_feminicidio"
        ]
    )
].copy()

base_consumada = base_letal[
    base_letal["tipo_evento"] == "consumado"
].copy()

base_tentativas = base_letal[
    base_letal["tipo_evento"] == "tentativa"
].copy()

print("\nBase letal, consumada y tentativas:")
print("Base letal:", base_letal.shape)
print("Base consumada:", base_consumada.shape)
print("Base tentativas:", base_tentativas.shape)


# ------------------------------------------------------------
# 13. Guardar base larga principal
# ------------------------------------------------------------

# Esta es la tabla más importante.
# Conserva municipio, mes, delito, modalidad, sexo, edad y víctimas.

columnas_base_larga = [
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
    "Rango de edad",
    "Mes_num",
    "Mes",
    "Victimas",
    "categoria_analisis",
    "tipo_evento"
]

base_letal_larga = base_letal[columnas_base_larga].copy()

guardar_csv(
    base_letal_larga,
    ANALYTIC_DIR / "01_base_letal_larga.csv"
)

base_consumada_larga = base_consumada[columnas_base_larga].copy()

guardar_csv(
    base_consumada_larga,
    ANALYTIC_DIR / "01b_base_consumada_larga.csv"
)


# ------------------------------------------------------------
# 14. Crear tabla municipal mensual de consumados
# ------------------------------------------------------------

municipios = (
    tabasco[
        [
            "Año",
            "Clave_Ent",
            "Entidad",
            "Cve. Municipio",
            "Municipio"
        ]
    ]
    .drop_duplicates()
    .copy()
)

meses_df = pd.DataFrame({
    "Mes": meses_disponibles
})

meses_df["Mes_num"] = meses_df["Mes"].map(ORDEN_MESES)

# Creamos una estructura completa municipio x mes.
# Esto sirve para que municipios sin víctimas no desaparezcan.
municipios["_key"] = 1
meses_df["_key"] = 1

skeleton = municipios.merge(meses_df, on="_key").drop(columns="_key")

municipal_largo = (
    base_consumada
    .groupby(
        [
            "Año",
            "Clave_Ent",
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

municipal_pivot = municipal_largo.pivot_table(
    index=[
        "Año",
        "Clave_Ent",
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

municipal_pivot.columns.name = None

municipal_mensual = skeleton.merge(
    municipal_pivot,
    on=[
        "Año",
        "Clave_Ent",
        "Entidad",
        "Cve. Municipio",
        "Municipio",
        "Mes_num",
        "Mes"
    ],
    how="left"
)

for col in ["homicidio_doloso", "homicidio_culposo", "feminicidio"]:
    if col not in municipal_mensual.columns:
        municipal_mensual[col] = 0
    municipal_mensual[col] = municipal_mensual[col].fillna(0)

municipal_mensual["total_intencional"] = (
    municipal_mensual["homicidio_doloso"]
    + municipal_mensual["feminicidio"]
)

municipal_mensual["total_homicidios_y_feminicidio"] = (
    municipal_mensual["homicidio_doloso"]
    + municipal_mensual["homicidio_culposo"]
    + municipal_mensual["feminicidio"]
)

# Calculamos días del mes para cada fila municipal.
municipal_mensual["dias_mes"] = municipal_mensual.apply(
    lambda fila: calendar.monthrange(
        int(fila["Año"]),
        int(fila["Mes_num"])
    )[1],
    axis=1
)

# Promedio diario municipal del homicidio total consumado:
# homicidio doloso + homicidio culposo + feminicidio, dividido entre días del mes.
municipal_mensual["promedio_diario_total_homicidios"] = (
    municipal_mensual["total_homicidios_y_feminicidio"]
    / municipal_mensual["dias_mes"]
)

municipal_mensual = municipal_mensual.sort_values(
    ["Municipio", "Mes_num"]
).reset_index(drop=True)

guardar_csv(
    municipal_mensual,
    ANALYTIC_DIR / "02_municipal_mensual_consumado.csv"
)


# ------------------------------------------------------------
# 15. Crear tabla estatal mensual de consumados
# ------------------------------------------------------------

estatal_mensual = (
    municipal_mensual
    .groupby(
        ["Año", "Clave_Ent", "Entidad", "Mes_num", "Mes"],
        as_index=False
    )
    [
        [
            "homicidio_doloso",
            "homicidio_culposo",
            "feminicidio",
            "total_intencional",
            "total_homicidios_y_feminicidio"
        ]
    ]
    .sum()
    .sort_values("Mes_num")
)

# Calculamos días del mes para cada mes estatal.
estatal_mensual["dias_mes"] = estatal_mensual.apply(
    lambda fila: calendar.monthrange(
        int(fila["Año"]),
        int(fila["Mes_num"])
    )[1],
    axis=1
)

# Promedio diario estatal del homicidio total consumado:
# homicidio doloso + homicidio culposo + feminicidio, dividido entre días del mes.
estatal_mensual["promedio_diario_total_homicidios"] = (
    estatal_mensual["total_homicidios_y_feminicidio"]
    / estatal_mensual["dias_mes"]
)

guardar_csv(
    estatal_mensual,
    ANALYTIC_DIR / "03_estatal_mensual_consumado.csv"
)


# ------------------------------------------------------------
# 16. Crear ranking municipal acumulado
# ------------------------------------------------------------

ranking_municipal = (
    municipal_mensual
    .groupby(
        ["Año", "Clave_Ent", "Entidad", "Cve. Municipio", "Municipio"],
        as_index=False
    )
    [
        [
            "homicidio_doloso",
            "homicidio_culposo",
            "feminicidio",
            "total_intencional",
            "total_homicidios_y_feminicidio"
        ]
    ]
    .sum()
)

total_estatal_intencional = ranking_municipal["total_intencional"].sum()
total_estatal_amplio = ranking_municipal["total_homicidios_y_feminicidio"].sum()

ranking_municipal["pct_total_intencional"] = ranking_municipal["total_intencional"].apply(
    lambda x: porcentaje_seguro(x, total_estatal_intencional)
)

ranking_municipal["pct_total_amplio"] = ranking_municipal["total_homicidios_y_feminicidio"].apply(
    lambda x: porcentaje_seguro(x, total_estatal_amplio)
)

ranking_municipal["rank_total_intencional"] = (
    ranking_municipal["total_intencional"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

ranking_municipal["rank_total_amplio"] = (
    ranking_municipal["total_homicidios_y_feminicidio"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

ranking_municipal = ranking_municipal.sort_values(
    ["rank_total_amplio", "Municipio"]
).reset_index(drop=True)

guardar_csv(
    ranking_municipal,
    ANALYTIC_DIR / "04_ranking_municipal_acumulado.csv"
)


# ------------------------------------------------------------
# 17. Crear matriz para heatmap municipio-mes
# ------------------------------------------------------------

heatmap_municipio_mes = municipal_mensual.pivot_table(
    index="Municipio",
    columns="Mes",
    values="total_homicidios_y_feminicidio",
    aggfunc="sum",
    fill_value=0
)

# Reordenar columnas según el orden de meses disponible.
heatmap_municipio_mes = heatmap_municipio_mes[
    meses_disponibles
]

heatmap_municipio_mes["Total"] = heatmap_municipio_mes.sum(axis=1)

heatmap_municipio_mes = heatmap_municipio_mes.sort_values(
    "Total",
    ascending=False
).reset_index()

guardar_csv(
    heatmap_municipio_mes,
    ANALYTIC_DIR / "05_heatmap_municipio_mes_total_amplio.csv"
)


# ------------------------------------------------------------
# 18. Crear tabla de modalidad de homicidio doloso
# ------------------------------------------------------------

modalidad_homicidio_doloso = (
    base_consumada[
        base_consumada["categoria_analisis"] == "homicidio_doloso"
    ]
    .groupby("Modalidad", as_index=False)["Victimas"]
    .sum()
    .sort_values("Victimas", ascending=False)
)

total_doloso = modalidad_homicidio_doloso["Victimas"].sum()

modalidad_homicidio_doloso["porcentaje"] = modalidad_homicidio_doloso["Victimas"].apply(
    lambda x: porcentaje_seguro(x, total_doloso)
)

guardar_csv(
    modalidad_homicidio_doloso,
    ANALYTIC_DIR / "06_modalidad_homicidio_doloso.csv"
)


# ------------------------------------------------------------
# 19. Crear tabla de modalidad de homicidio culposo
# ------------------------------------------------------------

modalidad_homicidio_culposo = (
    base_consumada[
        base_consumada["categoria_analisis"] == "homicidio_culposo"
    ]
    .groupby("Modalidad", as_index=False)["Victimas"]
    .sum()
    .sort_values("Victimas", ascending=False)
)

total_culposo = modalidad_homicidio_culposo["Victimas"].sum()

modalidad_homicidio_culposo["porcentaje"] = modalidad_homicidio_culposo["Victimas"].apply(
    lambda x: porcentaje_seguro(x, total_culposo)
)

guardar_csv(
    modalidad_homicidio_culposo,
    ANALYTIC_DIR / "07_modalidad_homicidio_culposo.csv"
)


# ------------------------------------------------------------
# 20. Crear tabla sexo-edad de consumados
# ------------------------------------------------------------

sexo_edad = (
    base_consumada
    .groupby(
        [
            "categoria_analisis",
            "Sexo",
            "Rango de edad"
        ],
        as_index=False
    )["Victimas"]
    .sum()
    .sort_values("Victimas", ascending=False)
)

guardar_csv(
    sexo_edad,
    ANALYTIC_DIR / "08_sexo_edad_consumado.csv"
)


# ------------------------------------------------------------
# 21. Crear tabla de tentativas municipal mensual
# ------------------------------------------------------------

tentativas_municipal = (
    base_tentativas
    .groupby(
        [
            "Año",
            "Clave_Ent",
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
    .sort_values(
        [
            "Municipio",
            "Mes_num",
            "categoria_analisis"
        ]
    )
)

guardar_csv(
    tentativas_municipal,
    ANALYTIC_DIR / "09_tentativas_municipal_mensual.csv"
)


# ------------------------------------------------------------
# 22. Crear tabla de tentativas estatal mensual
# ------------------------------------------------------------

tentativas_estatal = (
    base_tentativas
    .groupby(
        [
            "Año",
            "Clave_Ent",
            "Entidad",
            "Mes_num",
            "Mes",
            "categoria_analisis"
        ],
        as_index=False
    )["Victimas"]
    .sum()
    .sort_values(
        [
            "Mes_num",
            "categoria_analisis"
        ]
    )
)

guardar_csv(
    tentativas_estatal,
    ANALYTIC_DIR / "10_tentativas_estatal_mensual.csv"
)


# ------------------------------------------------------------
# 23. Crear tabla de promedio diario municipal mensual
# ------------------------------------------------------------

promedio_diario_municipal = municipal_mensual[
    [
        "Año",
        "Clave_Ent",
        "Entidad",
        "Cve. Municipio",
        "Municipio",
        "Mes_num",
        "Mes",
        "dias_mes",
        "homicidio_doloso",
        "homicidio_culposo",
        "feminicidio",
        "total_homicidios_y_feminicidio",
        "promedio_diario_total_homicidios"
    ]
].copy()

promedio_diario_municipal = promedio_diario_municipal.sort_values(
    ["Municipio", "Mes_num"]
).reset_index(drop=True)

guardar_csv(
    promedio_diario_municipal,
    ANALYTIC_DIR / "11_promedio_diario_municipal_mensual.csv"
)


# ------------------------------------------------------------
# 24. Crear tabla de promedio diario estatal mensual
# ------------------------------------------------------------

promedio_diario_estatal = estatal_mensual[
    [
        "Año",
        "Clave_Ent",
        "Entidad",
        "Mes_num",
        "Mes",
        "dias_mes",
        "homicidio_doloso",
        "homicidio_culposo",
        "feminicidio",
        "total_homicidios_y_feminicidio",
        "promedio_diario_total_homicidios"
    ]
].copy()

promedio_diario_estatal = promedio_diario_estatal.sort_values(
    "Mes_num"
).reset_index(drop=True)

guardar_csv(
    promedio_diario_estatal,
    ANALYTIC_DIR / "12_promedio_diario_estatal_mensual.csv"
)


# ------------------------------------------------------------
# 25. Crear resumen de control
# ------------------------------------------------------------

resumen_control = pd.DataFrame({
    "indicador": [
        "homicidio_doloso",
        "homicidio_culposo",
        "feminicidio",
        "total_intencional",
        "total_homicidios_y_feminicidio",
        "promedio_diario_estatal_periodo",
        "tentativa_homicidio_doloso",
        "tentativa_feminicidio"
    ],
    "victimas": [
        municipal_mensual["homicidio_doloso"].sum(),
        municipal_mensual["homicidio_culposo"].sum(),
        municipal_mensual["feminicidio"].sum(),
        municipal_mensual["total_intencional"].sum(),
        municipal_mensual["total_homicidios_y_feminicidio"].sum(),
        municipal_mensual["total_homicidios_y_feminicidio"].sum()
        / municipal_mensual[["Año", "Mes_num", "dias_mes"]].drop_duplicates()["dias_mes"].sum(),
        base_tentativas[
            base_tentativas["categoria_analisis"] == "tentativa_homicidio_doloso"
        ]["Victimas"].sum(),
        base_tentativas[
            base_tentativas["categoria_analisis"] == "tentativa_feminicidio"
        ]["Victimas"].sum()
    ]
})

guardar_csv(
    resumen_control,
    ANALYTIC_DIR / "00_resumen_control.csv"
)


# ------------------------------------------------------------
# 26. Mostrar resumen final en pantalla
# ------------------------------------------------------------

print("\n============================================================")
print("RESUMEN DE CONTROL")
print("============================================================")
print(resumen_control.to_string(index=False))

print("\n============================================================")
print("PROMEDIO DIARIO ESTATAL DE HOMICIDIO TOTAL CONSUMADO")
print("============================================================")
print(
    promedio_diario_estatal[
        [
            "Mes",
            "dias_mes",
            "homicidio_doloso",
            "homicidio_culposo",
            "feminicidio",
            "total_homicidios_y_feminicidio",
            "promedio_diario_total_homicidios"
        ]
    ].to_string(index=False)
)

print("\n============================================================")
print("TOP MUNICIPIOS POR TOTAL AMPLIO")
print("============================================================")
print(
    ranking_municipal[
        [
            "Municipio",
            "homicidio_doloso",
            "homicidio_culposo",
            "feminicidio",
            "total_intencional",
            "total_homicidios_y_feminicidio",
            "pct_total_amplio"
        ]
    ]
    .head(10)
    .to_string(index=False)
)

print("\n============================================================")
print("TABLAS GENERADAS EN:")
print("============================================================")
print(ANALYTIC_DIR)

print("\nProceso terminado correctamente.")