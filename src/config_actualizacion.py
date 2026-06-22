from __future__ import annotations

from pathlib import Path
import re
import unicodedata

import pandas as pd


MESES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

ALIAS_MESES = {
    "ene": 1,
    "enero": 1,
    "feb": 2,
    "febrero": 2,
    "mar": 3,
    "marzo": 3,
    "abr": 4,
    "abril": 4,
    "may": 5,
    "mayo": 5,
    "jun": 6,
    "junio": 6,
    "jul": 7,
    "julio": 7,
    "ago": 8,
    "agosto": 8,
    "sep": 9,
    "sept": 9,
    "septiembre": 9,
    "oct": 10,
    "octubre": 10,
    "nov": 11,
    "noviembre": 11,
    "dic": 12,
    "diciembre": 12,
}


def normalizar_nombre(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return normalized.lower()


def extraer_periodo_archivo(path: Path) -> tuple[int, int] | None:
    nombre = normalizar_nombre(path.stem)

    if "victimas" not in nombre or "municipal" not in nombre:
        return None

    aliases = "|".join(
        sorted(
            (re.escape(alias) for alias in ALIAS_MESES),
            key=len,
            reverse=True,
        )
    )

    match = re.search(
        rf"(?:^|[-_ ])({aliases})[-_ ]?(20\d{{2}})(?:$|[-_ ])",
        nombre,
    )

    if not match:
        return None

    alias, year = match.groups()
    return int(year), ALIAS_MESES[alias]


def seleccionar_csv_municipal_mas_reciente(
    raw_dir: Path,
    anio: int | None = None,
) -> Path:
    candidatos: list[tuple[int, int, float, str, Path]] = []

    for path in raw_dir.rglob("*.csv"):
        periodo = extraer_periodo_archivo(path)
        if periodo is None:
            continue

        year, month = periodo

        if anio is not None and year != anio:
            continue

        candidatos.append(
            (
                year,
                month,
                path.stat().st_mtime,
                normalizar_nombre(path.name),
                path,
            )
        )

    if not candidatos:
        esperado = f" del año {anio}" if anio is not None else ""
        raise FileNotFoundError(
            "No se encontró ningún CSV municipal de víctimas"
            f"{esperado} dentro de {raw_dir}. "
            "Ejemplo esperado: "
            "RNID-Victimas_Municipal-2026-jun2026.csv"
        )

    candidatos.sort()
    return candidatos[-1][-1]


def detectar_meses_disponibles(df: pd.DataFrame) -> list[str]:
    meses: list[str] = []

    for mes in MESES:
        if mes not in df.columns:
            continue

        valores = pd.to_numeric(df[mes], errors="coerce")

        if valores.notna().any():
            meses.append(mes)

    if not meses:
        raise ValueError(
            "El archivo no contiene información numérica en ninguna "
            "columna mensual."
        )

    return meses


def leer_csv_robusto(path: Path) -> pd.DataFrame:
    errors: list[str] = []

    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(
                path,
                encoding=encoding,
                low_memory=False,
            )
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")

    raise RuntimeError(
        "No fue posible leer el CSV. Codificaciones probadas:\n"
        + "\n".join(errors)
    )
