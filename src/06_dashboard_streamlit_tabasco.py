# ============================================================
# PROYECTO: Homicidios en Tabasco con datos del SESNSP/RNID
# SCRIPT 06: Dashboard interactivo en Streamlit
#
# OBJETIVO:
#   Crear un tablero interactivo para explorar:
#   1. Homicidio doloso
#   2. Homicidio culposo
#   3. Feminicidio
#   4. Total intencional
#   5. Total homicidios y feminicidio
#   6. Promedio diario
#   7. Ranking municipal
#   8. Heatmap municipio-mes
#   9. Mapa coroplético municipal
#   10. Modalidades
#   11. Sexo y edad
#   12. Tentativas
#
# AJUSTES INCLUIDOS:
#   - Usa geometría municipal oficial del INEGI para Tabasco.
#   - Evita el GeoJSON anterior incorrecto.
#   - El mapa muestra líneas de división municipal.
#   - El mapa muestra nombres de municipios.
#   - "No especificado" se conserva en tablas, pero no se pinta en el mapa.
#   - El mapa usa escala continua con raíz cuadrada.
#   - El selector "Mes para el mapa" muestra:
#       Enero, Febrero, Marzo, Abril...
#       Acumulado Enero - Abril
#     y se actualiza automáticamente cuando aparezcan nuevos meses.
#   - El mapa SIEMPRE respeta el panel lateral.
#   - Se elimina el botón "Aplicar filtro de municipios del panel lateral".
#
# NOTA METODOLÓGICA DEL MAPA:
#   La raíz cuadrada solo se usa para mejorar la visualización.
#   Los datos reales no se modifican.
#   Las tablas, hover y totales muestran víctimas reales.
#
# EJECUCIÓN:
#   python -m streamlit run src/06_dashboard_streamlit_tabasco.py
# ============================================================


# ------------------------------------------------------------
# 1. Importar librerías
# ------------------------------------------------------------

from pathlib import Path
import json
import unicodedata
import re
import urllib.request
import math

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import plotly.express as px
import plotly.graph_objects as go


# ------------------------------------------------------------
# 2. Configuración general del dashboard
# ------------------------------------------------------------

st.set_page_config(
    page_title="Homicidios Tabasco 2026",
    page_icon="📊",
    layout="wide"
)


# ------------------------------------------------------------
# 3. Definir rutas del proyecto
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

TABLES_DIR = BASE_DIR / "outputs" / "tables" / "analiticas"
FIGURES_DIR = BASE_DIR / "outputs" / "figures" / "analiticas"
REPORTS_DIR = BASE_DIR / "outputs" / "reportes"

GEO_DIR = BASE_DIR / "data" / "geo"
GEO_DIR.mkdir(parents=True, exist_ok=True)

REPORTE_EXCEL = REPORTS_DIR / "reporte_homicidios_tabasco_2026_ene_abr.xlsx"

# Archivo local del GeoJSON oficial de INEGI.
GEOJSON_TABASCO = GEO_DIR / "inegi_mgem_27_tabasco.geojson"

# Servicio oficial INEGI para áreas geoestadísticas municipales de Tabasco.
# 27 = clave geoestadística estatal de Tabasco.
GEOJSON_URL = "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/27"


# ------------------------------------------------------------
# 4. Escala continua recomendada para el mapa
# ------------------------------------------------------------

# Esta escala es continua, no por clases.
#
# Se usa junto con una transformación de raíz cuadrada:
#   valor_color = sqrt(víctimas)
#
# Eso permite que los municipios con valores bajos y medios
# sean más visibles cuando hay un municipio con valor muy alto.
#
# Importante:
#   Los datos reales NO se modifican.
#   Solo se transforma el valor usado para colorear.

ESCALA_CONTINUA_ROJO_SQRT = [
    [0.00, "#FFF5F5"],
    [0.50, "#EF7373"],
    [1.00, "#A80303"],
]


# ------------------------------------------------------------
# 5. Funciones auxiliares generales
# ------------------------------------------------------------

def normalizar_texto(valor):
    """
    Convierte texto a una forma más fácil de comparar:
    - minúsculas
    - sin acentos
    - sin espacios dobles

    Ejemplos:
        'Cárdenas' -> 'cardenas'
        'Jalpa de Méndez' -> 'jalpa de mendez'
    """
    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto)
    return texto


def separar_registros_no_geograficos(df, columna_municipio="Municipio"):
    """
    Separa registros que no pueden pintarse en un mapa.

    En la base municipal del SESNSP puede aparecer 'No especificado'.
    Ese valor sirve para conservar el dato estadístico, pero no es un
    municipio real y por lo tanto no tiene polígono en el GeoJSON.

    Devuelve:
        df_geo:
            registros que sí corresponden a municipios reales.

        df_no_geo:
            registros como 'No especificado', que se reportan aparte
            pero no se dibujan en el mapa.
    """

    valores_no_geograficos = {
        "no especificado",
        "sin especificar",
        "no determinado",
        "no identificado",
        "se ignora",
        "ignorado"
    }

    df_temp = df.copy()

    df_temp["_municipio_norm_temp"] = df_temp[columna_municipio].apply(
        normalizar_texto
    )

    df_no_geo = df_temp[
        df_temp["_municipio_norm_temp"].isin(valores_no_geograficos)
    ].copy()

    df_geo = df_temp[
        ~df_temp["_municipio_norm_temp"].isin(valores_no_geograficos)
    ].copy()

    df_geo = df_geo.drop(columns=["_municipio_norm_temp"])
    df_no_geo = df_no_geo.drop(columns=["_municipio_norm_temp"])

    return df_geo, df_no_geo


def extraer_puntos_de_geometria(geometry):
    """
    Extrae puntos lon/lat desde una geometría GeoJSON.

    Soporta:
        - Polygon
        - MultiPolygon

    Regresa una lista de pares:
        [(lon, lat), (lon, lat), ...]

    Esta función se usa para calcular un centro aproximado
    del municipio y colocar ahí el nombre.
    """

    puntos = []

    if geometry is None:
        return puntos

    tipo = geometry.get("type")
    coords = geometry.get("coordinates", [])

    if tipo == "Polygon":
        if len(coords) > 0:
            anillo_exterior = coords[0]
            for punto in anillo_exterior:
                if len(punto) >= 2:
                    puntos.append((punto[0], punto[1]))

    elif tipo == "MultiPolygon":
        poligonos = coords
        mejor_anillo = []

        for poligono in poligonos:
            if len(poligono) > 0:
                anillo_exterior = poligono[0]
                if len(anillo_exterior) > len(mejor_anillo):
                    mejor_anillo = anillo_exterior

        for punto in mejor_anillo:
            if len(punto) >= 2:
                puntos.append((punto[0], punto[1]))

    return puntos


def calcular_centroide_aproximado(geometry):
    """
    Calcula un centro aproximado para colocar etiquetas.

    No es un centroide geográfico perfecto.
    Es suficiente para ubicar el nombre del municipio en el tablero.

    Método:
        promedio de longitudes y latitudes del anillo exterior.
    """

    puntos = extraer_puntos_de_geometria(geometry)

    if len(puntos) == 0:
        return None, None

    lon = sum(p[0] for p in puntos) / len(puntos)
    lat = sum(p[1] for p in puntos) / len(puntos)

    return lon, lat


def agregar_valores_mapa_sqrt(df, columna_valor):
    """
    Agrega dos columnas para el mapa:

        valor_mapa:
            valor real del indicador seleccionado.

        valor_mapa_sqrt:
            raíz cuadrada del valor real.

    La columna valor_mapa_sqrt se usa solo para colorear.
    La columna valor_mapa mantiene el dato real.
    """

    df = df.copy()

    df["valor_mapa"] = pd.to_numeric(
        df[columna_valor],
        errors="coerce"
    ).fillna(0)

    df["valor_mapa_sqrt"] = df["valor_mapa"].apply(
        lambda x: math.sqrt(max(x, 0))
    )

    return df


def crear_ticks_colorbar(valor_maximo):
    """
    Crea etiquetas para la barra de color del mapa.

    Como el color usa sqrt(víctimas), internamente Plotly ve valores
    transformados. Para que el usuario lea víctimas reales, creamos:

        tickvals:
            valores transformados con sqrt.

        ticktext:
            valores reales mostrados en la leyenda.
    """

    try:
        vmax = int(math.ceil(float(valor_maximo)))
    except Exception:
        vmax = 0

    if vmax <= 0:
        return [0], ["0"]

    if vmax <= 5:
        ticks_reales = list(range(0, vmax + 1))
    else:
        ticks_reales = [
            0,
            int(round(vmax * 0.25)),
            int(round(vmax * 0.50)),
            int(round(vmax * 0.75)),
            vmax
        ]

    # Quitar duplicados y ordenar.
    ticks_reales = sorted(set(ticks_reales))

    # Asegurar que 0 y máximo estén presentes.
    if 0 not in ticks_reales:
        ticks_reales.insert(0, 0)

    if vmax not in ticks_reales:
        ticks_reales.append(vmax)

    tickvals = [math.sqrt(x) for x in ticks_reales]
    ticktext = [str(x) for x in ticks_reales]

    return tickvals, ticktext


def construir_opciones_periodo_mapa(meses_df):
    """
    Construye opciones dinámicas para el selector 'Mes para el mapa'.

    Ejemplo con enero-abril:
        Enero
        Febrero
        Marzo
        Abril
        Acumulado Enero - Abril

    Cuando el archivo tenga mayo:
        Enero
        Febrero
        Marzo
        Abril
        Mayo
        Acumulado Enero - Mayo

    Esta función usa los meses que estén disponibles y seleccionados
    en el panel lateral.
    """

    meses_df = meses_df.copy().sort_values("Mes_num")

    if meses_df.empty:
        return [], {}

    opciones = meses_df["Mes"].tolist()

    primer_mes = meses_df.iloc[0]["Mes"]
    ultimo_mes = meses_df.iloc[-1]["Mes"]

    etiqueta_acumulado = f"Acumulado {primer_mes} - {ultimo_mes}"

    opciones.append(etiqueta_acumulado)

    metadata = {}

    for _, fila in meses_df.iterrows():
        metadata[fila["Mes"]] = {
            "tipo": "mes",
            "meses": [fila["Mes"]],
            "titulo": fila["Mes"]
        }

    metadata[etiqueta_acumulado] = {
        "tipo": "acumulado",
        "meses": meses_df["Mes"].tolist(),
        "titulo": etiqueta_acumulado
    }

    return opciones, metadata


@st.cache_data
def leer_tabla(nombre_archivo):
    """
    Lee una tabla CSV desde outputs/tables/analiticas.

    st.cache_data guarda temporalmente el resultado.
    Esto evita que Streamlit lea el mismo archivo cada vez que cambias filtros.
    """

    ruta = TABLES_DIR / nombre_archivo

    if not ruta.exists():
        st.error(
            f"No encontré la tabla: {ruta}\n\n"
            "Primero corre el Script 03."
        )
        st.stop()

    return pd.read_csv(ruta)


@st.cache_data
def cargar_geojson_tabasco():
    """
    Descarga y carga el GeoJSON municipal oficial del INEGI para Tabasco.

    Servicio usado:
        https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/27

    El archivo se guarda localmente en:
        data/geo/inegi_mgem_27_tabasco.geojson

    A cada polígono se le agrega:
        municipio_geo
        municipio_norm
        label_lon
        label_lat

    municipio_norm será la llave de unión con la tabla del SESNSP.
    label_lon y label_lat se usan para colocar el nombre del municipio.
    """

    if not GEOJSON_TABASCO.exists():
        try:
            urllib.request.urlretrieve(GEOJSON_URL, GEOJSON_TABASCO)
        except Exception as e:
            st.error(
                "No pude descargar el GeoJSON municipal oficial de Tabasco desde INEGI.\n\n"
                "Revisa tu conexión a internet o descarga manualmente el archivo "
                "desde esta dirección:\n\n"
                f"{GEOJSON_URL}\n\n"
                "y guárdalo como:\n\n"
                f"{GEOJSON_TABASCO}\n\n"
                f"Error original: {e}"
            )
            st.stop()

    with open(GEOJSON_TABASCO, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    if "features" not in geojson:
        st.error(
            "El archivo descargado desde INEGI no tiene la estructura GeoJSON esperada. "
            "Falta la llave 'features'."
        )
        st.stop()

    posibles_campos_nombre = [
        "nomgeo",
        "NOMGEO",
        "nom_mun",
        "NOM_MUN",
        "municipio",
        "MUNICIPIO",
        "nombre",
        "Nombre",
        "NAME",
        "name"
    ]

    features_limpias = []

    for feature in geojson["features"]:

        props = feature.setdefault("properties", {})

        # El servicio de INEGI normalmente trae:
        # cvegeo, cve_ent, cve_mun, nomgeo.
        cve_ent = str(props.get("cve_ent", props.get("CVE_ENT", ""))).zfill(2)

        # Por seguridad, filtramos solo Tabasco.
        # Si cve_ent no viene en el servicio, permitimos vacío porque la URL ya filtra 27.
        if cve_ent not in ["", "27"]:
            continue

        nombre_municipio = None

        for campo in posibles_campos_nombre:
            if campo in props and props[campo] not in [None, ""]:
                nombre_municipio = props[campo]
                break

        if nombre_municipio is None:
            st.error(
                "No pude detectar el nombre municipal dentro del GeoJSON del INEGI.\n\n"
                f"Campos disponibles en una geometría: {list(props.keys())}"
            )
            st.stop()

        props["municipio_geo"] = str(nombre_municipio)
        props["municipio_norm"] = normalizar_texto(nombre_municipio)

        label_lon, label_lat = calcular_centroide_aproximado(feature.get("geometry"))
        props["label_lon"] = label_lon
        props["label_lat"] = label_lat

        features_limpias.append(feature)

    geojson["features"] = features_limpias

    # Validación mínima: Tabasco debe tener 17 municipios.
    municipios_detectados = sorted(
        {
            feature["properties"]["municipio_norm"]
            for feature in geojson["features"]
        }
    )

    if len(municipios_detectados) != 17:
        st.warning(
            "Advertencia: el GeoJSON cargado no contiene exactamente 17 municipios. "
            f"Municipios detectados: {len(municipios_detectados)}.\n\n"
            "Revisa la fuente geográfica."
        )

    # Validación para evitar el error del GeoJSON anterior.
    if "catazaja" in municipios_detectados:
        st.error(
            "El GeoJSON contiene Catazajá, que pertenece a Chiapas. "
            "Esto indica que se está usando un mapa incorrecto. "
            "Borra el archivo GeoJSON local y vuelve a cargar el tablero."
        )
        st.stop()

    return geojson


def formatear_numero(valor):
    """
    Formatea números enteros con separador de miles.
    """
    try:
        return f"{float(valor):,.0f}"
    except Exception:
        return valor


def formatear_decimal(valor):
    """
    Formatea números decimales con dos posiciones.
    """
    try:
        return f"{float(valor):,.2f}"
    except Exception:
        return valor


def guardar_figura_streamlit(fig):
    """
    Muestra una figura de matplotlib en Streamlit.
    """
    st.pyplot(fig, clear_figure=True)


def agregar_etiquetas_barras_horizontales(ax, decimales=0):
    """
    Agrega etiquetas al final de barras horizontales.
    """
    for barra in ax.patches:
        ancho = barra.get_width()
        y = barra.get_y() + barra.get_height() / 2

        if decimales == 0:
            etiqueta = f" {ancho:.0f}"
        else:
            etiqueta = f" {ancho:.2f}"

        ax.text(
            ancho,
            y,
            etiqueta,
            va="center",
            fontsize=9
        )


# ------------------------------------------------------------
# 6. Cargar tablas analíticas
# ------------------------------------------------------------

resumen_control = leer_tabla("00_resumen_control.csv")
estatal_mensual = leer_tabla("03_estatal_mensual_consumado.csv")
municipal_mensual = leer_tabla("02_municipal_mensual_consumado.csv")
ranking_municipal_base = leer_tabla("04_ranking_municipal_acumulado.csv")
heatmap_base = leer_tabla("05_heatmap_municipio_mes_total_amplio.csv")
modalidad_doloso = leer_tabla("06_modalidad_homicidio_doloso.csv")
modalidad_culposo = leer_tabla("07_modalidad_homicidio_culposo.csv")
sexo_edad = leer_tabla("08_sexo_edad_consumado.csv")
tentativas_estatal = leer_tabla("10_tentativas_estatal_mensual.csv")
tentativas_municipal = leer_tabla("09_tentativas_municipal_mensual.csv")
promedio_diario_estatal = leer_tabla("12_promedio_diario_estatal_mensual.csv")
promedio_diario_municipal = leer_tabla("11_promedio_diario_municipal_mensual.csv")

geojson_tabasco = cargar_geojson_tabasco()


# ------------------------------------------------------------
# 7. Preparar campos auxiliares
# ------------------------------------------------------------

municipal_mensual["municipio_norm"] = municipal_mensual["Municipio"].apply(
    normalizar_texto
)

municipal_mensual_geo, municipal_mensual_no_geo = separar_registros_no_geograficos(
    municipal_mensual,
    columna_municipio="Municipio"
)

municipal_mensual_geo["municipio_norm"] = municipal_mensual_geo["Municipio"].apply(
    normalizar_texto
)

municipal_mensual_no_geo["municipio_norm"] = municipal_mensual_no_geo["Municipio"].apply(
    normalizar_texto
)

municipios_geo = []

for feature in geojson_tabasco["features"]:
    props = feature["properties"]
    municipios_geo.append(
        {
            "municipio_geo": props.get("municipio_geo"),
            "municipio_norm": props.get("municipio_norm"),
            "label_lon": props.get("label_lon"),
            "label_lat": props.get("label_lat")
        }
    )

municipios_geo_df = pd.DataFrame(municipios_geo).drop_duplicates()


# ------------------------------------------------------------
# 8. Título principal
# ------------------------------------------------------------

st.title("📊 Dashboard de Homicidios y Feminicidio en Tabasco")
st.caption(
    "Fuente principal: SESNSP/RNID. Geometría municipal: INEGI, Marco Geoestadístico municipal."
)

st.markdown(
    """
    Este tablero analiza víctimas de **homicidio doloso**, **homicidio culposo**
    y **feminicidio consumado**.

    Las **tentativas** se presentan por separado y no se suman al total de homicidios consumados.
    """
)


# ------------------------------------------------------------
# 9. Sidebar: filtros generales
# ------------------------------------------------------------

st.sidebar.title("Filtros generales")

meses_disponibles = (
    municipal_mensual[["Mes_num", "Mes"]]
    .drop_duplicates()
    .sort_values("Mes_num")
)

lista_meses = meses_disponibles["Mes"].tolist()

meses_seleccionados = st.sidebar.multiselect(
    "Selecciona mes(es)",
    options=lista_meses,
    default=lista_meses
)

lista_municipios = sorted(municipal_mensual["Municipio"].dropna().unique().tolist())

municipios_seleccionados = st.sidebar.multiselect(
    "Selecciona municipio(s)",
    options=lista_municipios,
    default=lista_municipios
)

indicador_seleccionado = st.sidebar.selectbox(
    "Indicador principal",
    options=[
        "total_homicidios_y_feminicidio",
        "total_intencional",
        "homicidio_doloso",
        "homicidio_culposo",
        "feminicidio"
    ],
    index=0
)

st.sidebar.markdown("---")

mostrar_tablas = st.sidebar.checkbox(
    "Mostrar tablas debajo de las gráficas",
    value=True
)

top_n = st.sidebar.slider(
    "Número de municipios en rankings",
    min_value=5,
    max_value=17,
    value=10,
    step=1
)


# ------------------------------------------------------------
# 10. Aplicar filtros generales
# ------------------------------------------------------------

municipal_filtrado = municipal_mensual[
    municipal_mensual["Mes"].isin(meses_seleccionados)
    &
    municipal_mensual["Municipio"].isin(municipios_seleccionados)
].copy()

estatal_filtrado = estatal_mensual[
    estatal_mensual["Mes"].isin(meses_seleccionados)
].copy()

promedio_estatal_filtrado = promedio_diario_estatal[
    promedio_diario_estatal["Mes"].isin(meses_seleccionados)
].copy()

tentativas_estatal_filtrado = tentativas_estatal[
    tentativas_estatal["Mes"].isin(meses_seleccionados)
].copy()

tentativas_municipal_filtrado = tentativas_municipal[
    tentativas_municipal["Mes"].isin(meses_seleccionados)
    &
    tentativas_municipal["Municipio"].isin(municipios_seleccionados)
].copy()


# ------------------------------------------------------------
# 11. Cálculos principales para tarjetas métricas
# ------------------------------------------------------------

total_doloso = municipal_filtrado["homicidio_doloso"].sum()
total_culposo = municipal_filtrado["homicidio_culposo"].sum()
total_feminicidio = municipal_filtrado["feminicidio"].sum()
total_intencional = municipal_filtrado["total_intencional"].sum()
total_amplio = municipal_filtrado["total_homicidios_y_feminicidio"].sum()

dias_periodo = (
    municipal_filtrado[["Año", "Mes_num", "dias_mes"]]
    .drop_duplicates()["dias_mes"]
    .sum()
)

if dias_periodo > 0:
    promedio_diario_periodo = total_amplio / dias_periodo
else:
    promedio_diario_periodo = 0

ranking_filtrado = (
    municipal_filtrado
    .groupby("Municipio", as_index=False)
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

ranking_filtrado["promedio_diario_periodo"] = (
    ranking_filtrado["total_homicidios_y_feminicidio"] / dias_periodo
    if dias_periodo > 0
    else 0
)

ranking_filtrado = ranking_filtrado.sort_values(
    indicador_seleccionado,
    ascending=False
)

if not ranking_filtrado.empty:
    municipio_top = ranking_filtrado.iloc[0]["Municipio"]
    valor_top = ranking_filtrado.iloc[0][indicador_seleccionado]
else:
    municipio_top = "Sin datos"
    valor_top = 0


# ------------------------------------------------------------
# 12. Tarjetas resumen
# ------------------------------------------------------------

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total amplio", formatear_numero(total_amplio))
col2.metric("Total intencional", formatear_numero(total_intencional))
col3.metric("Homicidio culposo", formatear_numero(total_culposo))
col4.metric("Feminicidio", formatear_numero(total_feminicidio))
col5.metric("Promedio diario", formatear_decimal(promedio_diario_periodo))

st.info(
    f"Municipio con mayor valor en el indicador seleccionado: "
    f"**{municipio_top}** ({formatear_numero(valor_top)} víctimas)."
)


# ------------------------------------------------------------
# 13. Crear pestañas del dashboard
# ------------------------------------------------------------

tab_resumen, tab_estado, tab_municipios, tab_mapa, tab_heatmap, tab_modalidad, tab_perfil, tab_tentativas, tab_reporte = st.tabs(
    [
        "Resumen",
        "Estado",
        "Municipios",
        "Mapa",
        "Heatmap",
        "Modalidad",
        "Sexo y edad",
        "Tentativas",
        "Reporte"
    ]
)


# ------------------------------------------------------------
# 14. Pestaña: Resumen
# ------------------------------------------------------------

with tab_resumen:
    st.subheader("Resumen ejecutivo")

    st.markdown(
        """
        **Definiciones usadas en el tablero:**

        - **Total amplio:** homicidio doloso + homicidio culposo + feminicidio.
        - **Total intencional:** homicidio doloso + feminicidio.
        - **Promedio diario:** total amplio dividido entre los días del mes o periodo seleccionado.
        - **Tentativas:** se analizan aparte; no se suman al total consumado.
        - **No especificado:** se conserva en tablas y totales, pero no se pinta en mapas.
        """
    )

    resumen_df = pd.DataFrame({
        "Indicador": [
            "Homicidio doloso",
            "Homicidio culposo",
            "Feminicidio",
            "Total intencional",
            "Total amplio",
            "Días del periodo seleccionado",
            "Promedio diario del periodo",
            "Municipio principal"
        ],
        "Valor": [
            total_doloso,
            total_culposo,
            total_feminicidio,
            total_intencional,
            total_amplio,
            dias_periodo,
            round(promedio_diario_periodo, 2),
            municipio_top
        ]
    })

    st.dataframe(resumen_df, use_container_width=True, hide_index=True)

    if mostrar_tablas:
        st.markdown("### Ranking filtrado")
        st.dataframe(ranking_filtrado, use_container_width=True, hide_index=True)


# ------------------------------------------------------------
# 15. Pestaña: Estado
# ------------------------------------------------------------

with tab_estado:
    st.subheader("Análisis estatal mensual")

    estatal_plot = estatal_filtrado.sort_values("Mes_num")

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.bar(
        estatal_plot["Mes"],
        estatal_plot["homicidio_doloso"],
        label="Homicidio doloso"
    )

    ax.bar(
        estatal_plot["Mes"],
        estatal_plot["homicidio_culposo"],
        bottom=estatal_plot["homicidio_doloso"],
        label="Homicidio culposo"
    )

    bottom_feminicidio = (
        estatal_plot["homicidio_doloso"]
        + estatal_plot["homicidio_culposo"]
    )

    ax.bar(
        estatal_plot["Mes"],
        estatal_plot["feminicidio"],
        bottom=bottom_feminicidio,
        label="Feminicidio"
    )

    for i, total in enumerate(estatal_plot["total_homicidios_y_feminicidio"]):
        ax.text(
            i,
            total,
            f"{total:.0f}",
            ha="center",
            va="bottom",
            fontsize=9
        )

    ax.set_title("Tabasco: homicidio total consumado por mes")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Víctimas")
    ax.legend()

    guardar_figura_streamlit(fig)

    st.markdown("### Promedio diario estatal")

    fig, ax = plt.subplots(figsize=(10, 4))

    promedio_plot = promedio_estatal_filtrado.sort_values("Mes_num")

    ax.plot(
        promedio_plot["Mes"],
        promedio_plot["promedio_diario_total_homicidios"],
        marker="o"
    )

    for x, y in zip(
        promedio_plot["Mes"],
        promedio_plot["promedio_diario_total_homicidios"]
    ):
        ax.text(
            x,
            y,
            f"{y:.2f}",
            ha="center",
            va="bottom",
            fontsize=9
        )

    ax.set_title("Promedio diario estatal de homicidio total consumado")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Promedio diario")
    ax.grid(axis="y", alpha=0.3)

    guardar_figura_streamlit(fig)

    if mostrar_tablas:
        st.markdown("### Tabla estatal mensual")
        st.dataframe(estatal_plot, use_container_width=True, hide_index=True)


# ------------------------------------------------------------
# 16. Pestaña: Municipios
# ------------------------------------------------------------

with tab_municipios:
    st.subheader("Análisis municipal")

    top_municipios = ranking_filtrado.head(top_n)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(
        top_municipios["Municipio"],
        top_municipios[indicador_seleccionado]
    )

    ax.invert_yaxis()
    agregar_etiquetas_barras_horizontales(ax)

    ax.set_title(f"Top {top_n} municipios por {indicador_seleccionado}")
    ax.set_xlabel("Víctimas")
    ax.set_ylabel("Municipio")

    guardar_figura_streamlit(fig)

    st.markdown("### Promedio diario municipal del periodo")

    top_promedio = (
        ranking_filtrado
        .sort_values("promedio_diario_periodo", ascending=False)
        .head(top_n)
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(
        top_promedio["Municipio"],
        top_promedio["promedio_diario_periodo"]
    )

    ax.invert_yaxis()
    agregar_etiquetas_barras_horizontales(ax, decimales=2)

    ax.set_title(f"Top {top_n} municipios por promedio diario del periodo")
    ax.set_xlabel("Promedio diario")
    ax.set_ylabel("Municipio")

    guardar_figura_streamlit(fig)

    if mostrar_tablas:
        st.markdown("### Tabla municipal filtrada")
        st.dataframe(ranking_filtrado, use_container_width=True, hide_index=True)


# ------------------------------------------------------------
# 17. Pestaña: Mapa coroplético municipal
# ------------------------------------------------------------

with tab_mapa:
    st.subheader("Mapa coroplético municipal con escala continua ajustada")

    st.markdown(
        """
        Este mapa usa geometría municipal oficial del INEGI para Tabasco.
        La escala de color es **continua**, pero usa una transformación de **raíz cuadrada**
        para que los municipios con valores bajos y medios se distingan mejor.
        Los datos reales se conservan en el hover y en las tablas.
        """
    )

    # El mapa respeta SIEMPRE los meses y municipios seleccionados
    # en el panel lateral.
    meses_mapa_df = (
        meses_disponibles[
            meses_disponibles["Mes"].isin(meses_seleccionados)
        ]
        .drop_duplicates()
        .sort_values("Mes_num")
        .copy()
    )

    opciones_periodo_mapa, metadata_periodo_mapa = construir_opciones_periodo_mapa(
        meses_mapa_df
    )

    if len(opciones_periodo_mapa) == 0:
        st.warning("Selecciona al menos un mes en el panel lateral para construir el mapa.")
    else:
        col_mapa_1, col_mapa_2, col_mapa_3 = st.columns([1, 1, 1])

        with col_mapa_1:
            opcion_periodo_mapa = st.selectbox(
                "Mes para el mapa",
                options=opciones_periodo_mapa,
                index=len(opciones_periodo_mapa) - 1
            )

        opciones_indicador_mapa = {
            "Homicidio doloso": "homicidio_doloso",
            "Homicidio culposo": "homicidio_culposo",
            "Feminicidio": "feminicidio",
            "Total intencional": "total_intencional",
            "Total homicidios y feminicidio": "total_homicidios_y_feminicidio",
        }

        with col_mapa_2:
            etiqueta_indicador_mapa = st.selectbox(
                "Indicador para el mapa",
                options=list(opciones_indicador_mapa.keys()),
                index=4
            )

        indicador_mapa = opciones_indicador_mapa[etiqueta_indicador_mapa]

        with col_mapa_3:
            mostrar_nombres_mapa = st.checkbox(
                "Mostrar nombres de municipios",
                value=True
            )

        periodo_info = metadata_periodo_mapa[opcion_periodo_mapa]
        meses_periodo_mapa = periodo_info["meses"]
        titulo_periodo_mapa = periodo_info["titulo"]

        # ----------------------------------------------------
        # Preparar base del mapa
        # ----------------------------------------------------

        mapa_base = municipal_mensual_geo[
            municipal_mensual_geo["Mes"].isin(meses_periodo_mapa)
            &
            municipal_mensual_geo["Municipio"].isin(municipios_seleccionados)
        ].copy()

        mapa_no_geo = municipal_mensual_no_geo[
            municipal_mensual_no_geo["Mes"].isin(meses_periodo_mapa)
            &
            municipal_mensual_no_geo["Municipio"].isin(municipios_seleccionados)
        ].copy()

        municipios_seleccionados_norm = [
            normalizar_texto(municipio)
            for municipio in municipios_seleccionados
        ]

        municipios_geo_mapa_df = municipios_geo_df[
            municipios_geo_df["municipio_norm"].isin(municipios_seleccionados_norm)
        ].copy()

        if municipios_geo_mapa_df.empty:
            st.warning(
                "No hay municipios geográficos seleccionados para el mapa. "
                "Si solo seleccionaste 'No especificado', recuerda que no se puede pintar en el mapa."
            )
        else:
            mapa_base["municipio_norm"] = mapa_base["Municipio"].apply(normalizar_texto)

            mapa_df = (
                mapa_base
                .groupby(["Municipio", "municipio_norm"], as_index=False)
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

            # Unimos contra los municipios del GeoJSON seleccionados
            # para respetar SIEMPRE el panel lateral.
            mapa_df = municipios_geo_mapa_df.merge(
                mapa_df,
                on="municipio_norm",
                how="left"
            )

            mapa_df["Municipio"] = mapa_df["Municipio"].fillna(mapa_df["municipio_geo"])

            for col in [
                "homicidio_doloso",
                "homicidio_culposo",
                "feminicidio",
                "total_intencional",
                "total_homicidios_y_feminicidio"
            ]:
                mapa_df[col] = mapa_df[col].fillna(0)

            municipios_tabla = set(mapa_base["municipio_norm"].unique())
            municipios_geo_set = set(municipios_geo_df["municipio_norm"].unique())

            municipios_sin_geo = sorted(list(municipios_tabla - municipios_geo_set))

            if len(municipios_sin_geo) > 0:
                st.warning(
                    "Hay municipios reales en la tabla que no coincidieron con el GeoJSON del INEGI:\n\n"
                    + ", ".join(municipios_sin_geo)
                )

            if not mapa_no_geo.empty:
                no_geo_resumen = mapa_no_geo[
                    [
                        "homicidio_doloso",
                        "homicidio_culposo",
                        "feminicidio",
                        "total_intencional",
                        "total_homicidios_y_feminicidio"
                    ]
                ].sum()

                valor_no_geo = no_geo_resumen[indicador_mapa]

                if valor_no_geo > 0:
                    st.info(
                        f"Nota: existen **{valor_no_geo:.0f} víctimas** en el indicador "
                        f"**{etiqueta_indicador_mapa}** registradas como **No especificado**. "
                        "Se conservan en las tablas, pero no se pintan en el mapa porque no tienen municipio geográfico."
                    )

            # Agregamos valor real y valor transformado.
            mapa_df = agregar_valores_mapa_sqrt(
                mapa_df,
                columna_valor=indicador_mapa
            )

            valor_maximo_real = mapa_df["valor_mapa"].max()
            valor_maximo_sqrt = mapa_df["valor_mapa_sqrt"].max()

            if valor_maximo_real == 0:
                st.info("Con los filtros seleccionados, todos los municipios tienen valor cero.")

            tickvals, ticktext = crear_ticks_colorbar(valor_maximo_real)

            fig_mapa = px.choropleth(
                mapa_df,
                geojson=geojson_tabasco,
                locations="municipio_norm",
                featureidkey="properties.municipio_norm",
                color="valor_mapa_sqrt",
                hover_name="Municipio",
                hover_data={
                    "municipio_norm": False,
                    "municipio_geo": False,
                    "label_lon": False,
                    "label_lat": False,
                    "valor_mapa_sqrt": False,
                    "valor_mapa": True,
                    "homicidio_doloso": True,
                    "homicidio_culposo": True,
                    "feminicidio": True,
                    "total_intencional": True,
                    "total_homicidios_y_feminicidio": True,
                },
                color_continuous_scale=ESCALA_CONTINUA_ROJO_SQRT,
                range_color=(0, max(valor_maximo_sqrt, 1)),
                labels={
                    "valor_mapa_sqrt": "Víctimas",
                    "valor_mapa": etiqueta_indicador_mapa,
                    "homicidio_doloso": "Homicidio doloso",
                    "homicidio_culposo": "Homicidio culposo",
                    "feminicidio": "Feminicidio",
                    "total_intencional": "Total intencional",
                    "total_homicidios_y_feminicidio": "Total homicidios y feminicidio",
                },
                title=f"Tabasco: {etiqueta_indicador_mapa} por municipio ({titulo_periodo_mapa})"
            )

            # Líneas de división municipal.
            fig_mapa.update_traces(
                marker_line_color="#222222",
                marker_line_width=1.4,
                selector=dict(type="choropleth")
            )

            fig_mapa.update_geos(
                fitbounds="locations",
                visible=False,
                showcountries=False,
                showcoastlines=False,
                showland=True,
                landcolor="rgb(245,245,245)",
                bgcolor="rgba(0,0,0,0)"
            )

            fig_mapa.update_layout(
                height=720,
                margin={"r": 0, "t": 60, "l": 0, "b": 0},
                coloraxis_colorbar={
                    "title": "Víctimas",
                    "tickvals": tickvals,
                    "ticktext": ticktext
                }
            )

            if mostrar_nombres_mapa:

                etiquetas_df = mapa_df[
                    [
                        "Municipio",
                        "municipio_norm",
                        "label_lon",
                        "label_lat",
                        indicador_mapa
                    ]
                ].copy()

                etiquetas_df = etiquetas_df.dropna(subset=["label_lon", "label_lat"])

                fig_mapa.add_trace(
                    go.Scattergeo(
                        lon=etiquetas_df["label_lon"],
                        lat=etiquetas_df["label_lat"],
                        text=etiquetas_df["Municipio"],
                        mode="text",
                        textfont=dict(
                            size=9,
                            color="black"
                        ),
                        hoverinfo="skip",
                        showlegend=False
                    )
                )

            st.plotly_chart(
                fig_mapa,
                use_container_width=True
            )

            st.caption(
                "Nota visual: el color se calcula con raíz cuadrada para mejorar la lectura. "
                "La barra, el hover y las tablas muestran víctimas reales. "
                "El mapa respeta los meses y municipios seleccionados en el panel lateral."
            )

            st.markdown("### Tabla base del mapa")

            tabla_mapa = mapa_df[
                [
                    "Municipio",
                    "valor_mapa",
                    "homicidio_doloso",
                    "homicidio_culposo",
                    "feminicidio",
                    "total_intencional",
                    "total_homicidios_y_feminicidio"
                ]
            ].rename(
                columns={
                    "valor_mapa": etiqueta_indicador_mapa
                }
            ).sort_values(
                etiqueta_indicador_mapa,
                ascending=False
            )

            st.dataframe(
                tabla_mapa,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                label="Descargar tabla del mapa en CSV",
                data=tabla_mapa.to_csv(index=False, encoding="utf-8-sig"),
                file_name="tabla_mapa_coropletico_tabasco.csv",
                mime="text/csv"
            )


# ------------------------------------------------------------
# 18. Pestaña: Heatmap
# ------------------------------------------------------------

with tab_heatmap:
    st.subheader("Heatmap municipio-mes")

    heatmap_filtrado = (
        municipal_filtrado
        .pivot_table(
            index="Municipio",
            columns="Mes",
            values="total_homicidios_y_feminicidio",
            aggfunc="sum",
            fill_value=0
        )
    )

    meses_ordenados_filtrados = (
        municipal_filtrado[["Mes_num", "Mes"]]
        .drop_duplicates()
        .sort_values("Mes_num")["Mes"]
        .tolist()
    )

    heatmap_filtrado = heatmap_filtrado[
        [m for m in meses_ordenados_filtrados if m in heatmap_filtrado.columns]
    ]

    heatmap_filtrado["Total"] = heatmap_filtrado.sum(axis=1)

    heatmap_filtrado = heatmap_filtrado.sort_values(
        "Total",
        ascending=False
    )

    matriz = heatmap_filtrado.drop(columns="Total").values
    municipios_heatmap = heatmap_filtrado.index.tolist()
    columnas_mes = heatmap_filtrado.drop(columns="Total").columns.tolist()

    if matriz.size == 0:
        st.warning("No hay datos para construir el heatmap con los filtros actuales.")
    else:
        fig, ax = plt.subplots(figsize=(10, 8))

        im = ax.imshow(
            matriz,
            aspect="auto",
            cmap="viridis_r"
        )

        ax.set_xticks(range(len(columnas_mes)))
        ax.set_xticklabels(columnas_mes)

        ax.set_yticks(range(len(municipios_heatmap)))
        ax.set_yticklabels(municipios_heatmap)

        for i in range(len(municipios_heatmap)):
            for j in range(len(columnas_mes)):
                valor = matriz[i, j]

                texto = ax.text(
                    j,
                    i,
                    f"{valor:.0f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold"
                )

                texto.set_path_effects([
                    path_effects.withStroke(
                        linewidth=1.5,
                        foreground="black"
                    )
                ])

        ax.set_title("Heatmap municipio-mes: total amplio")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Municipio")

        fig.colorbar(im, ax=ax, label="Víctimas")

        guardar_figura_streamlit(fig)

    if mostrar_tablas:
        st.markdown("### Tabla base del heatmap")
        st.dataframe(
            heatmap_filtrado.reset_index(),
            use_container_width=True,
            hide_index=True
        )


# ------------------------------------------------------------
# 19. Pestaña: Modalidad
# ------------------------------------------------------------

with tab_modalidad:
    st.subheader("Modalidad del homicidio")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Homicidio doloso")

        modalidad_doloso_plot = modalidad_doloso.sort_values(
            "Victimas",
            ascending=True
        )

        fig, ax = plt.subplots(figsize=(7, 5))

        ax.barh(
            modalidad_doloso_plot["Modalidad"],
            modalidad_doloso_plot["Victimas"]
        )

        agregar_etiquetas_barras_horizontales(ax)

        ax.set_title("Modalidad del homicidio doloso")
        ax.set_xlabel("Víctimas")
        ax.set_ylabel("Modalidad")

        guardar_figura_streamlit(fig)

        if mostrar_tablas:
            st.dataframe(
                modalidad_doloso,
                use_container_width=True,
                hide_index=True
            )

    with col_b:
        st.markdown("### Homicidio culposo")

        modalidad_culposo_plot = modalidad_culposo.sort_values(
            "Victimas",
            ascending=True
        )

        fig, ax = plt.subplots(figsize=(7, 5))

        ax.barh(
            modalidad_culposo_plot["Modalidad"],
            modalidad_culposo_plot["Victimas"]
        )

        agregar_etiquetas_barras_horizontales(ax)

        ax.set_title("Modalidad del homicidio culposo")
        ax.set_xlabel("Víctimas")
        ax.set_ylabel("Modalidad")

        guardar_figura_streamlit(fig)

        if mostrar_tablas:
            st.dataframe(
                modalidad_culposo,
                use_container_width=True,
                hide_index=True
            )


# ------------------------------------------------------------
# 20. Pestaña: Sexo y edad
# ------------------------------------------------------------

with tab_perfil:
    st.subheader("Perfil de víctimas por sexo y edad")

    sexo_edad_total = (
        sexo_edad
        .groupby(["Sexo", "Rango de edad"], as_index=False)["Victimas"]
        .sum()
    )

    sexo_edad_pivot = sexo_edad_total.pivot_table(
        index="Rango de edad",
        columns="Sexo",
        values="Victimas",
        aggfunc="sum",
        fill_value=0
    )

    orden_edad = [
        "Menores de edad",
        "18 y más",
        "18 a 29 años",
        "30 a 60 años",
        "60 y más",
        "No especificado"
    ]

    orden_existente = [x for x in orden_edad if x in sexo_edad_pivot.index]
    resto = [x for x in sexo_edad_pivot.index if x not in orden_existente]

    sexo_edad_pivot = sexo_edad_pivot.loc[orden_existente + resto]

    fig, ax = plt.subplots(figsize=(10, 5))

    sexo_edad_pivot.plot(
        kind="bar",
        stacked=True,
        ax=ax
    )

    ax.set_title("Víctimas por sexo y rango de edad")
    ax.set_xlabel("Rango de edad")
    ax.set_ylabel("Víctimas")
    ax.legend(title="Sexo")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)

    guardar_figura_streamlit(fig)

    if mostrar_tablas:
        st.dataframe(
            sexo_edad_total.sort_values("Victimas", ascending=False),
            use_container_width=True,
            hide_index=True
        )


# ------------------------------------------------------------
# 21. Pestaña: Tentativas
# ------------------------------------------------------------

with tab_tentativas:
    st.subheader("Tentativas")

    st.warning(
        "Las tentativas se presentan por separado. "
        "No se suman al total de homicidios consumados."
    )

    if tentativas_estatal_filtrado.empty:
        st.info("No hay tentativas con los filtros seleccionados.")
    else:
        tentativas_pivot = tentativas_estatal_filtrado.pivot_table(
            index=["Mes_num", "Mes"],
            columns="categoria_analisis",
            values="Victimas",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        tentativas_pivot = tentativas_pivot.sort_values("Mes_num")

        columnas_tentativas = [
            c for c in tentativas_pivot.columns
            if c not in ["Mes_num", "Mes"]
        ]

        fig, ax = plt.subplots(figsize=(10, 5))

        tentativas_pivot.set_index("Mes")[columnas_tentativas].plot(
            kind="bar",
            ax=ax
        )

        ax.set_title("Tentativas estatales por mes")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Víctimas")
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        ax.legend(title="Categoría")

        guardar_figura_streamlit(fig)

    if mostrar_tablas:
        st.markdown("### Tentativas estatales")
        st.dataframe(
            tentativas_estatal_filtrado,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Tentativas municipales")
        st.dataframe(
            tentativas_municipal_filtrado,
            use_container_width=True,
            hide_index=True
        )


# ------------------------------------------------------------
# 22. Pestaña: Reporte
# ------------------------------------------------------------

with tab_reporte:
    st.subheader("Reporte Excel")

    if REPORTE_EXCEL.exists():
        st.success("Reporte Excel disponible.")

        with open(REPORTE_EXCEL, "rb") as archivo:
            st.download_button(
                label="Descargar reporte Excel",
                data=archivo,
                file_name=REPORTE_EXCEL.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning(
            "Todavía no encontré el reporte Excel. "
            "Corre primero el Script 05."
        )

    st.markdown("### Archivos del proyecto")

    st.write("Carpeta de tablas analíticas:")
    st.code(str(TABLES_DIR))

    st.write("Carpeta de gráficas:")
    st.code(str(FIGURES_DIR))

    st.write("Carpeta de reportes:")
    st.code(str(REPORTS_DIR))

    st.write("Carpeta de insumos geográficos:")
    st.code(str(GEO_DIR))


# ------------------------------------------------------------
# 23. Pie metodológico
# ------------------------------------------------------------

st.markdown("---")
st.caption(
    "Nota: el total amplio corresponde a homicidio doloso + homicidio culposo + feminicidio consumado. "
    "El total intencional corresponde a homicidio doloso + feminicidio. "
    "Las tentativas se analizan por separado. "
    "Los registros No especificado se conservan en tablas y totales, pero no se pintan en el mapa. "
    "La geometría municipal proviene del servicio vectorial del Marco Geoestadístico del INEGI. "
    "El mapa usa una escala continua con transformación de raíz cuadrada solo para mejorar la visualización."
)