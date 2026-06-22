from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd

from config_actualizacion import (
    detectar_meses_disponibles,
    leer_csv_robusto,
    seleccionar_csv_municipal_mas_reciente,
)


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
RAW_DIR = BASE_DIR / "data" / "raw"
ANALYTIC_DIR = BASE_DIR / "outputs" / "tables" / "analiticas"
TABLES_DIR = BASE_DIR / "outputs" / "tables"
REPORTS_DIR = BASE_DIR / "outputs" / "reportes"

SCRIPTS = [
    SRC_DIR / "02_explorar_delitos_tabasco.py",
    SRC_DIR / "03_calcular_homicidio_feminicidio_municipal.py",
    SRC_DIR / "04_graficas_significativas_tabasco.py",
    SRC_DIR / "05_reporte_excel_tabasco.py",
]


def ejecutar(script: Path) -> None:
    if not script.exists():
        raise FileNotFoundError(f"No se encontró el script: {script}")

    print("\n" + "=" * 78)
    print(f"EJECUTANDO: {script.name}")
    print("=" * 78)

    subprocess.run(
        [sys.executable, str(script)],
        cwd=BASE_DIR,
        check=True,
    )


def validar_resultados(ultimo_mes: str) -> None:
    archivos = [
        ANALYTIC_DIR / "02_municipal_mensual_consumado.csv",
        ANALYTIC_DIR / "03_estatal_mensual_consumado.csv",
        ANALYTIC_DIR / "05_heatmap_municipio_mes_total_amplio.csv",
        ANALYTIC_DIR / "10_tentativas_estatal_mensual.csv",
        ANALYTIC_DIR / "12_promedio_diario_estatal_mensual.csv",
    ]

    for path in archivos:
        if not path.exists():
            raise FileNotFoundError(
                f"No se generó el archivo analítico: {path}"
            )

        df = pd.read_csv(path)

        if "Mes" not in df.columns:
            continue

        meses = (
            df["Mes"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        if ultimo_mes not in meses:
            raise RuntimeError(
                f"{path.name} no contiene el último mes esperado: "
                f"{ultimo_mes}. Meses encontrados: {meses}"
            )

    reporte = (
        REPORTS_DIR
        / "reporte_homicidios_tabasco_2026_actual.xlsx"
    )

    if not reporte.exists():
        raise FileNotFoundError(
            f"No se generó el reporte estable: {reporte}"
        )


def limpiar_salidas_antiguas() -> None:
    for pattern in (
        "tabasco_estatal_homicidio_feminicidio_2026_ene_*.csv",
        "tabasco_municipal_homicidio_feminicidio_2026_ene_*.csv",
    ):
        for path in TABLES_DIR.glob(pattern):
            if not path.name.endswith("_actual.csv"):
                path.unlink(missing_ok=True)

    for path in REPORTS_DIR.glob(
        "reporte_homicidios_tabasco_2026_ene_*.xlsx"
    ):
        if path.name != "reporte_homicidios_tabasco_2026_actual.xlsx":
            path.unlink(missing_ok=True)


def main() -> None:
    archivo = seleccionar_csv_municipal_mas_reciente(
        RAW_DIR,
        anio=2026,
    )

    df = leer_csv_robusto(archivo)
    meses = detectar_meses_disponibles(df)
    ultimo_mes = meses[-1]

    print("Archivo mensual seleccionado automáticamente:")
    print(archivo)
    print("\nMeses detectados:")
    print(meses)
    print(f"\nÚltimo mes detectado: {ultimo_mes}")

    for script in SCRIPTS:
        ejecutar(script)

    validar_resultados(ultimo_mes)
    limpiar_salidas_antiguas()

    print("\n" + "=" * 78)
    print("ACTUALIZACIÓN MENSUAL TERMINADA CORRECTAMENTE")
    print("=" * 78)
    print(f"Archivo fuente: {archivo.name}")
    print(f"Periodo detectado: Enero - {ultimo_mes}")
    print(
        "Reporte: "
        "outputs/reportes/"
        "reporte_homicidios_tabasco_2026_actual.xlsx"
    )


if __name__ == "__main__":
    main()
