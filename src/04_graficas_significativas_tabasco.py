# ============================================================
# PROYECTO: Homicidios en Tabasco con datos del SESNSP/RNID
# SCRIPT 04: Gráficas significativas para Tabasco y municipios
#
# OBJETIVO:
#   Generar visualizaciones útiles a partir de las tablas
#   analíticas creadas en el Script 03.
#
# ENTRADAS:
#   outputs/tables/analiticas/
#
# SALIDAS:
#   outputs/figures/analiticas/
#
# CAMBIO IMPORTANTE EN ESTA VERSIÓN:
#   En el heatmap municipio-mes:
#   - Se invierte la escala de colores con cmap="viridis_r".
#   - Los valores altos quedan en tonos oscuros/morados.
#   - Los valores bajos quedan en tonos amarillos/claros.
#   - Los números dentro del heatmap se ponen en blanco.
#   - Además, se agrega un borde oscuro muy delgado al texto
#     para que los números se lean mejor.
# ============================================================


# ------------------------------------------------------------
# 1. Importar librerías
# ------------------------------------------------------------

from pathlib import Path
import textwrap

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects


# ------------------------------------------------------------
# 2. Definir rutas del proyecto
# ------------------------------------------------------------

# Carpeta principal del proyecto.
BASE_DIR = Path("/Users/soto/homicidios_tabasco")

# Carpeta donde están las tablas generadas por el script 03.
ANALYTIC_TABLES_DIR = BASE_DIR / "outputs" / "tables" / "analiticas"

# Carpeta donde vamos a guardar las gráficas.
FIGURES_DIR = BASE_DIR / "outputs" / "figures" / "analiticas"

# Si la carpeta de figuras no existe, Python la crea.
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 3. Funciones auxiliares
# ------------------------------------------------------------

def leer_tabla(nombre_archivo):
    """
    Lee una tabla CSV desde outputs/tables/analiticas.

    Esta función evita repetir muchas veces:
        pd.read_csv(...)

    También revisa si el archivo existe. Si no existe,
    manda un error claro indicando que primero debe correrse
    el script 03.
    """
    ruta = ANALYTIC_TABLES_DIR / nombre_archivo

    if not ruta.exists():
        raise FileNotFoundError(
            f"No encontré la tabla: {ruta}\n"
            "Primero corre el script 03."
        )

    return pd.read_csv(ruta)


def guardar_figura(nombre_archivo):
    """
    Guarda la figura actual en outputs/figures/analiticas.

    plt.tight_layout() ajusta espacios para evitar que títulos,
    ejes o etiquetas se encimen.

    bbox_inches='tight' ayuda a que la imagen no salga recortada.
    """
    ruta = FIGURES_DIR / nombre_archivo
    plt.tight_layout()
    plt.savefig(ruta, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Gráfica guardada: {ruta}")


def agregar_etiquetas_barras_horizontales(ax):
    """
    Agrega etiquetas numéricas al final de cada barra horizontal.

    ax.patches contiene las barras dibujadas en la gráfica.
    Cada barra tiene ancho, altura y posición.
    """
    for barra in ax.patches:
        ancho = barra.get_width()
        y = barra.get_y() + barra.get_height() / 2

        ax.text(
            ancho,
            y,
            f" {ancho:.0f}",
            va="center",
            fontsize=9
        )


def envolver_texto(texto, ancho=18):
    """
    Divide textos largos en varias líneas.

    Esto sirve para que etiquetas largas no se encimen,
    sobre todo en ejes con nombres extensos.
    """
    return "\n".join(textwrap.wrap(str(texto), width=ancho))


# ------------------------------------------------------------
# 4. Leer tablas generadas por el script 03
# ------------------------------------------------------------

# Tabla estatal mensual con homicidio doloso, culposo, feminicidio,
# total intencional, total amplio y promedio diario.
estatal_mensual = leer_tabla("03_estatal_mensual_consumado.csv")

# Tabla municipal mensual.
municipal_mensual = leer_tabla("02_municipal_mensual_consumado.csv")

# Ranking acumulado por municipio.
ranking_municipal = leer_tabla("04_ranking_municipal_acumulado.csv")

# Matriz municipio-mes para heatmap.
heatmap_municipio_mes = leer_tabla("05_heatmap_municipio_mes_total_amplio.csv")

# Modalidad del homicidio doloso.
modalidad_doloso = leer_tabla("06_modalidad_homicidio_doloso.csv")

# Modalidad del homicidio culposo.
modalidad_culposo = leer_tabla("07_modalidad_homicidio_culposo.csv")

# Tabla de sexo y edad.
sexo_edad = leer_tabla("08_sexo_edad_consumado.csv")

# Tentativas estatales.
tentativas_estatal = leer_tabla("10_tentativas_estatal_mensual.csv")

# Promedio diario municipal mensual.
promedio_diario_municipal = leer_tabla("11_promedio_diario_municipal_mensual.csv")

# Promedio diario estatal mensual.
promedio_diario_estatal = leer_tabla("12_promedio_diario_estatal_mensual.csv")


# ------------------------------------------------------------
# 5. Ordenar tablas por mes
# ------------------------------------------------------------

# Esto asegura que los meses aparezcan en orden cronológico.
estatal_mensual = estatal_mensual.sort_values("Mes_num")
promedio_diario_estatal = promedio_diario_estatal.sort_values("Mes_num")
tentativas_estatal = tentativas_estatal.sort_values(["Mes_num", "categoria_analisis"])


# ------------------------------------------------------------
# 6. Gráfica 01: Barras apiladas estatal por mes
# ------------------------------------------------------------

# Esta gráfica muestra la evolución mensual del total amplio:
# homicidio doloso + homicidio culposo + feminicidio.
#
# La ventaja de apilar las barras es que puedes ver:
# - cuánto aporta el homicidio doloso,
# - cuánto aporta el culposo,
# - y cuánto aporta el feminicidio.

fig, ax = plt.subplots(figsize=(10, 6))

meses = estatal_mensual["Mes"]

ax.bar(
    meses,
    estatal_mensual["homicidio_doloso"],
    label="Homicidio doloso"
)

ax.bar(
    meses,
    estatal_mensual["homicidio_culposo"],
    bottom=estatal_mensual["homicidio_doloso"],
    label="Homicidio culposo"
)

bottom_feminicidio = (
    estatal_mensual["homicidio_doloso"]
    + estatal_mensual["homicidio_culposo"]
)

ax.bar(
    meses,
    estatal_mensual["feminicidio"],
    bottom=bottom_feminicidio,
    label="Feminicidio"
)

# Agregamos el total arriba de cada barra.
for i, total in enumerate(estatal_mensual["total_homicidios_y_feminicidio"]):
    ax.text(
        i,
        total,
        f"{total:.0f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

ax.set_title(
    "Tabasco: víctimas de homicidio total consumado por mes, 2026\n"
    "Homicidio doloso + homicidio culposo + feminicidio"
)
ax.set_xlabel("Mes")
ax.set_ylabel("Víctimas")
ax.legend()

guardar_figura("01_estatal_barras_apiladas_homicidio_total.png")


# ------------------------------------------------------------
# 7. Gráfica 02: Promedio diario estatal por mes
# ------------------------------------------------------------

# Esta gráfica muestra el ritmo diario de homicidios totales consumados.
#
# Fórmula:
# promedio diario =
# total_homicidios_y_feminicidio / días del mes

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(
    promedio_diario_estatal["Mes"],
    promedio_diario_estatal["promedio_diario_total_homicidios"],
    marker="o"
)

# Agregamos etiquetas con dos decimales.
for x, y in zip(
    promedio_diario_estatal["Mes"],
    promedio_diario_estatal["promedio_diario_total_homicidios"]
):
    ax.text(
        x,
        y,
        f"{y:.2f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

ax.set_title(
    "Tabasco: promedio diario de homicidio total consumado por mes, 2026"
)
ax.set_xlabel("Mes")
ax.set_ylabel("Promedio diario de víctimas")
ax.grid(axis="y", alpha=0.3)

guardar_figura("02_promedio_diario_estatal_homicidio_total.png")


# ------------------------------------------------------------
# 8. Gráfica 03: Ranking municipal total amplio
# ------------------------------------------------------------

# Esta gráfica muestra los 10 municipios con más víctimas del total amplio:
# homicidio doloso + homicidio culposo + feminicidio.

top_amplio = (
    ranking_municipal
    .sort_values("total_homicidios_y_feminicidio", ascending=False)
    .head(10)
    .copy()
)

fig, ax = plt.subplots(figsize=(10, 7))

ax.barh(
    top_amplio["Municipio"],
    top_amplio["total_homicidios_y_feminicidio"]
)

ax.invert_yaxis()
agregar_etiquetas_barras_horizontales(ax)

ax.set_title(
    "Tabasco: municipios con más víctimas de homicidio total consumado\n"
    "Enero-abril 2026"
)
ax.set_xlabel("Víctimas")
ax.set_ylabel("Municipio")

guardar_figura("03_ranking_municipal_total_amplio.png")


# ------------------------------------------------------------
# 9. Gráfica 04: Ranking municipal total intencional
# ------------------------------------------------------------

# Esta gráfica muestra violencia letal intencional:
# homicidio doloso + feminicidio.
#
# No incluye homicidio culposo porque el culposo no es intencional.

top_intencional = (
    ranking_municipal
    .sort_values("total_intencional", ascending=False)
    .head(10)
    .copy()
)

fig, ax = plt.subplots(figsize=(10, 7))

ax.barh(
    top_intencional["Municipio"],
    top_intencional["total_intencional"]
)

ax.invert_yaxis()
agregar_etiquetas_barras_horizontales(ax)

ax.set_title(
    "Tabasco: municipios con más víctimas de violencia letal intencional\n"
    "Homicidio doloso + feminicidio, enero-abril 2026"
)
ax.set_xlabel("Víctimas")
ax.set_ylabel("Municipio")

guardar_figura("04_ranking_municipal_total_intencional.png")


# ------------------------------------------------------------
# 10. Gráfica 05: Heatmap municipio-mes
# ------------------------------------------------------------

# Esta gráfica es una matriz:
# - Filas: municipios.
# - Columnas: meses.
# - Color: número de víctimas.
#
# CAMBIO SOLICITADO:
# Antes la escala era:
#   morado = bajo / cero
#   amarillo = alto
#
# Ahora usamos cmap="viridis_r", que invierte la escala:
#   amarillo = bajo / cero
#   morado/oscuro = alto
#
# Además, los números dentro de cada celda se colocan en blanco.
# Para mejorar la lectura, agregamos un borde negro delgado
# alrededor del texto blanco.

heatmap_df = heatmap_municipio_mes.copy()

# Detectamos cuáles columnas son meses.
# La tabla trae:
# Municipio | Enero | Febrero | Marzo | Abril | Total
#
# Entonces quitamos Municipio y Total para quedarnos solo con meses.
columnas_no_mes = ["Municipio", "Total"]
columnas_mes = [c for c in heatmap_df.columns if c not in columnas_no_mes]

# Ordenamos municipios de mayor a menor total.
heatmap_df = heatmap_df.sort_values("Total", ascending=False)

# Convertimos la parte de meses a una matriz numérica.
# imshow necesita una matriz de números.
matriz = heatmap_df[columnas_mes].values

# Lista de municipios para ponerlos en el eje Y.
municipios = heatmap_df["Municipio"].tolist()

fig, ax = plt.subplots(figsize=(11, 8))

# Aquí está el cambio central:
# cmap="viridis_r" invierte la escala de colores.
im = ax.imshow(
    matriz,
    aspect="auto",
    cmap="viridis_r"
)

# Configuramos las etiquetas del eje X con los meses.
ax.set_xticks(range(len(columnas_mes)))
ax.set_xticklabels(columnas_mes)

# Configuramos las etiquetas del eje Y con los municipios.
ax.set_yticks(range(len(municipios)))
ax.set_yticklabels(municipios)

# Escribimos el valor numérico dentro de cada celda.
for i in range(len(municipios)):
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

        # Este borde negro ayuda a que el número blanco se vea
        # incluso sobre fondos claros.
        texto.set_path_effects([
            path_effects.withStroke(
                linewidth=1.5,
                foreground="black"
            )
        ])

ax.set_title(
    "Tabasco: mapa de calor municipio-mes\n"
    "Homicidio doloso + culposo + feminicidio, 2026"
)
ax.set_xlabel("Mes")
ax.set_ylabel("Municipio")

# Barra lateral que explica la escala de color.
fig.colorbar(im, ax=ax, label="Víctimas")

guardar_figura("05_heatmap_municipio_mes_total_amplio.png")


# ------------------------------------------------------------
# 11. Gráfica 06: Modalidad de homicidio doloso
# ------------------------------------------------------------

# Esta gráfica muestra con qué modalidad se registró
# el homicidio doloso: arma de fuego, arma blanca,
# otro elemento, no especificado, etc.

modalidad_doloso = modalidad_doloso.sort_values("Victimas", ascending=True)

fig, ax = plt.subplots(figsize=(10, 6))

ax.barh(
    modalidad_doloso["Modalidad"],
    modalidad_doloso["Victimas"]
)

agregar_etiquetas_barras_horizontales(ax)

ax.set_title(
    "Tabasco: modalidad del homicidio doloso consumado\n"
    "Enero-abril 2026"
)
ax.set_xlabel("Víctimas")
ax.set_ylabel("Modalidad")

guardar_figura("06_modalidad_homicidio_doloso.png")


# ------------------------------------------------------------
# 12. Gráfica 07: Modalidad de homicidio culposo
# ------------------------------------------------------------

# Esta gráfica separa la lógica del homicidio culposo:
# accidente de tránsito, otro elemento, arma de fuego,
# arma blanca o no especificado.

modalidad_culposo = modalidad_culposo.sort_values("Victimas", ascending=True)

fig, ax = plt.subplots(figsize=(10, 6))

ax.barh(
    modalidad_culposo["Modalidad"],
    modalidad_culposo["Victimas"]
)

agregar_etiquetas_barras_horizontales(ax)

ax.set_title(
    "Tabasco: modalidad del homicidio culposo consumado\n"
    "Enero-abril 2026"
)
ax.set_xlabel("Víctimas")
ax.set_ylabel("Modalidad")

guardar_figura("07_modalidad_homicidio_culposo.png")


# ------------------------------------------------------------
# 13. Gráfica 08: Víctimas por sexo y edad
# ------------------------------------------------------------

# Esta gráfica ayuda a perfilar a las víctimas:
# sexo y rango de edad.
#
# Sumamos las categorías consumadas:
# homicidio doloso + homicidio culposo + feminicidio.

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

# Orden recomendado para que la gráfica sea más legible.
orden_edad = [
    "Menores de edad",
    "18 y más",
    "18 a 29 años",
    "30 a 60 años",
    "60 y más",
    "No especificado"
]

# Conservamos solo los rangos que existan.
orden_existente = [x for x in orden_edad if x in sexo_edad_pivot.index]

# Si aparece algún rango adicional, lo agregamos al final.
resto = [x for x in sexo_edad_pivot.index if x not in orden_existente]

sexo_edad_pivot = sexo_edad_pivot.loc[orden_existente + resto]

fig, ax = plt.subplots(figsize=(11, 6))

sexo_edad_pivot.plot(
    kind="bar",
    stacked=True,
    ax=ax
)

ax.set_title(
    "Tabasco: víctimas de homicidio total consumado por sexo y rango de edad\n"
    "Enero-abril 2026"
)
ax.set_xlabel("Rango de edad")
ax.set_ylabel("Víctimas")

# Mejoramos la lectura de etiquetas largas.
ax.set_xticklabels(
    [envolver_texto(x.get_text(), 14) for x in ax.get_xticklabels()],
    rotation=0
)

ax.legend(title="Sexo")

guardar_figura("08_sexo_edad_consumado.png")


# ------------------------------------------------------------
# 14. Gráfica 09: Tentativas estatales por mes
# ------------------------------------------------------------

# Las tentativas NO se suman a homicidio consumado.
# Se grafican aparte porque son violencia letal no consumada.

if tentativas_estatal.empty:
    print("No hay registros de tentativas para graficar.")
else:
    tentativas_pivot = tentativas_estatal.pivot_table(
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

    ax.set_title(
        "Tabasco: tentativas de homicidio y feminicidio por mes\n"
        "No se suman a homicidios consumados"
    )
    ax.set_xlabel("Mes")
    ax.set_ylabel("Víctimas")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    ax.legend(title="Categoría")

    guardar_figura("09_tentativas_estatales_mes.png")


# ------------------------------------------------------------
# 15. Gráfica 10: Promedio diario municipal acumulado
# ------------------------------------------------------------

# Para municipios, calculamos el promedio diario del periodo completo:
#
# promedio diario municipal del periodo =
# total amplio municipal enero-abril / días acumulados del periodo.
#
# El total amplio municipal es:
# homicidio doloso + homicidio culposo + feminicidio.

dias_periodo = (
    promedio_diario_estatal[
        ["Año", "Mes_num", "dias_mes"]
    ]
    .drop_duplicates()["dias_mes"]
    .sum()
)

promedio_municipal_periodo = (
    ranking_municipal[
        [
            "Municipio",
            "total_homicidios_y_feminicidio"
        ]
    ]
    .copy()
)

promedio_municipal_periodo["promedio_diario_periodo"] = (
    promedio_municipal_periodo["total_homicidios_y_feminicidio"]
    / dias_periodo
)

promedio_municipal_periodo = promedio_municipal_periodo.sort_values(
    "promedio_diario_periodo",
    ascending=False
).head(10)

fig, ax = plt.subplots(figsize=(10, 7))

ax.barh(
    promedio_municipal_periodo["Municipio"],
    promedio_municipal_periodo["promedio_diario_periodo"]
)

ax.invert_yaxis()

# Como aquí hay decimales, las etiquetas van con dos decimales.
for barra in ax.patches:
    ancho = barra.get_width()
    y = barra.get_y() + barra.get_height() / 2

    ax.text(
        ancho,
        y,
        f" {ancho:.2f}",
        va="center",
        fontsize=9
    )

ax.set_title(
    "Tabasco: promedio diario municipal de homicidio total consumado\n"
    "Enero-abril 2026"
)
ax.set_xlabel("Promedio diario de víctimas")
ax.set_ylabel("Municipio")

guardar_figura("10_promedio_diario_municipal_periodo.png")


# ------------------------------------------------------------
# 16. Guardar resumen de gráficas generadas
# ------------------------------------------------------------

# Esta tabla funciona como índice:
# indica qué archivo se creó y para qué sirve analíticamente.

graficas = pd.DataFrame({
    "archivo": [
        "01_estatal_barras_apiladas_homicidio_total.png",
        "02_promedio_diario_estatal_homicidio_total.png",
        "03_ranking_municipal_total_amplio.png",
        "04_ranking_municipal_total_intencional.png",
        "05_heatmap_municipio_mes_total_amplio.png",
        "06_modalidad_homicidio_doloso.png",
        "07_modalidad_homicidio_culposo.png",
        "08_sexo_edad_consumado.png",
        "09_tentativas_estatales_mes.png",
        "10_promedio_diario_municipal_periodo.png"
    ],
    "uso_analitico": [
        "Evolución estatal mensual del homicidio total consumado.",
        "Ritmo diario estatal de víctimas por mes.",
        "Concentración territorial del total amplio.",
        "Concentración territorial de violencia letal intencional.",
        "Picos municipales por mes con escala invertida.",
        "Composición del homicidio doloso por modalidad.",
        "Composición del homicidio culposo por modalidad.",
        "Perfil general de víctimas por sexo y edad.",
        "Violencia letal no consumada, separada del total.",
        "Promedio diario municipal para comparación territorial."
    ]
})

salida_resumen_graficas = FIGURES_DIR / "00_resumen_graficas_generadas.csv"

graficas.to_csv(
    salida_resumen_graficas,
    index=False,
    encoding="utf-8-sig"
)

print("\nResumen de gráficas generado:")
print(salida_resumen_graficas)

print("\nProceso terminado correctamente.")
print("Carpeta de salida:")
print(FIGURES_DIR)