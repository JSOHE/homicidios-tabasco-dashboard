# ============================================================
# PROYECTO: Homicidios en Tabasco con datos del SESNSP
# SCRIPT 01: Explorar el archivo descargado
# AUTOR: Juan Carlos Soto
# OBJETIVO:
#   1. Ubicar el archivo del SESNSP dentro de data/raw
#   2. Leer el archivo con pandas
#   3. Mostrar las columnas para entender su estructura
# ============================================================


# ------------------------------------------------------------
# 1. Importamos las herramientas que vamos a usar
# ------------------------------------------------------------

# pathlib nos ayuda a trabajar con rutas de archivos y carpetas.
# Es más ordenado que escribir rutas como texto normal.
from pathlib import Path

# pandas es la biblioteca principal para trabajar tablas de datos en Python.
# Con pandas podemos leer CSV, Excel, filtrar, agrupar y resumir datos.
import pandas as pd


# ------------------------------------------------------------
# 2. Definimos la ubicación principal del proyecto
# ------------------------------------------------------------

# Esta es la carpeta principal de tu proyecto.
# Todo lo que hagamos va a salir de aquí.
BASE_DIR = Path("/Users/soto/homicidios_tabasco")

# Esta es la carpeta donde guardaremos los archivos originales descargados.
RAW_DIR = BASE_DIR / "data" / "raw"


# ------------------------------------------------------------
# 3. Buscamos archivos dentro de data/raw
# ------------------------------------------------------------

# Aquí le pedimos a Python que busque archivos CSV dentro de data/raw.
# rglob significa "buscar también dentro de subcarpetas".
archivos_csv = list(RAW_DIR.rglob("*.csv"))

# Aquí buscamos archivos Excel.
archivos_excel = list(RAW_DIR.rglob("*.xlsx")) + list(RAW_DIR.rglob("*.xls"))

# Unimos todos los archivos encontrados en una sola lista.
archivos_encontrados = archivos_csv + archivos_excel


# ------------------------------------------------------------
# 4. Revisamos si Python encontró algún archivo
# ------------------------------------------------------------

print("Carpeta donde estoy buscando archivos:")
print(RAW_DIR)

print("\nArchivos encontrados:")
for archivo in archivos_encontrados:
    print("-", archivo)


# Si no encontró ningún archivo, detenemos el programa con un mensaje claro.
if len(archivos_encontrados) == 0:
    raise FileNotFoundError(
        "No encontré archivos CSV o Excel en data/raw. "
        "Primero descarga la base del SESNSP y guárdala en esa carpeta."
    )


# ------------------------------------------------------------
# 5. Seleccionamos el primer archivo encontrado
# ------------------------------------------------------------

# Por ahora tomamos el primer archivo encontrado.
# Más adelante haremos esto más inteligente.
archivo_datos = archivos_encontrados[0]

print("\nVoy a leer este archivo:")
print(archivo_datos)


# ------------------------------------------------------------
# 6. Leemos el archivo con pandas
# ------------------------------------------------------------


# Si el archivo termina en .csv, lo leemos como CSV.
if archivo_datos.suffix.lower() == ".csv":

    # Algunos archivos oficiales no vienen guardados en UTF-8.
    # Por eso vamos a intentar leer el archivo con varias codificaciones.
    #
    # utf-8: codificación moderna común.
    # utf-8-sig: variante de UTF-8 usada a veces por Excel.
    # latin-1: muy común en archivos con acentos y ñ.
    # cp1252: muy común en archivos generados desde Windows/Excel.
    codificaciones = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    # Creamos una variable vacía donde guardaremos el DataFrame cuando logremos leerlo.
    df = None

    # Probamos una codificación por una.
    for encoding in codificaciones:
        try:
            print(f"\nIntentando leer CSV con encoding: {encoding}")

            df = pd.read_csv(archivo_datos, encoding=encoding)

            print(f"Archivo leído correctamente con encoding: {encoding}")

            # Si funcionó, salimos del ciclo.
            break

        except UnicodeDecodeError:
            print(f"No funcionó con encoding: {encoding}")

    # Si después de intentar todas las codificaciones df sigue vacío,
    # entonces detenemos el programa con un mensaje claro.
    if df is None:
        raise UnicodeDecodeError(
            "No se pudo leer el archivo con las codificaciones probadas."
        )

# Si el archivo termina en .xlsx o .xls, lo leemos como Excel.
elif archivo_datos.suffix.lower() in [".xlsx", ".xls"]:
    df = pd.read_excel(archivo_datos)

# Si no es CSV ni Excel, mostramos un error.
else:
    raise ValueError("El archivo no es CSV ni Excel.")


# ------------------------------------------------------------
# 7. Mostramos información básica del archivo
# ------------------------------------------------------------

print("\nEl archivo fue leído correctamente.")

print("\nNúmero de filas y columnas:")
print(df.shape)

print("\nColumnas del archivo:")
print(df.columns.tolist())

print("\nPrimeras 5 filas del archivo:")
print(df.head())