"""Presentación de resultados: consola y export a CSV."""

import logging

import pandas as pd

from .screener import COLUMNAS_MOSTRAR

logger = logging.getLogger(__name__)


def format_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    """Prepara una copia legible de los candidatos (capitalización en B)."""
    df = candidates[COLUMNAS_MOSTRAR].copy()
    df["Market Capitalization"] = (
        (df["Market Capitalization"] / 1_000_000_000).round(2).astype(str) + " B"
    )
    return df


def show_candidates(candidates: pd.DataFrame) -> None:
    """Imprime los candidatos por consola."""
    if candidates.empty:
        logger.info("Ningun candidato cumple todos los criterios hoy.")
        return

    print(f"\n Encontrado(s) {len(candidates)} candidato(s):\n")
    print(format_candidates(candidates).to_string(index=False))


def export_candidates(candidates: pd.DataFrame, path: str) -> None:
    """Exporta los candidatos a CSV (o Excel si el path termina en .xlsx)."""
    if candidates.empty:
        logger.info("Nada que exportar: ningun candidato cumple los criterios.")
        return

    df = format_candidates(candidates)
    if path.lower().endswith(".xlsx"):
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)
    logger.info(f"Exportados {len(df)} candidatos a {path}")
