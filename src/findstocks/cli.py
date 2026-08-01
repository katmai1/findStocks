"""Interfaz de línea de comandos."""

import argparse
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

from .config import ScreenerConfig
from .logging_setup import setup_logging
from .output import export_candidates, show_candidates
from .screener import StocksFinder


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Script para encontrar entradas en acciones")

    parser.add_argument(
        "-c", "--config",
        type=str,
        default="default.toml",
        help="Ruta al archivo de configuración"
    )
    parser.add_argument(
        "-e", "--show-earnings",
        action="store_true",
        help="Muestra candidatos aunque haya 'earnings' cerca (desactiva ese filtro).",
    )
    parser.add_argument("-o", "--output", help="Exporta los resultados a un archivo CSV o XLSX")
    parser.add_argument("-v", "--verbose", action="store_true", help="Muestra logs detallados (debug)")

    args = parser.parse_args(argv)
    return args


def build_config(c) -> ScreenerConfig:
    return ScreenerConfig(
        markets = c['general']['markets'],
        top_n_cap = c['general']['top_percent'],
        max_price = c['general']['price_max'],
        min_volume = c['general']['volume_min'],
        days_min_earnings= c['general']['earning_days'],
        long_enabled = c['general']['long_enabled'],
        short_enabled = c['general']['short_enabled'],
        max_stocks = c['general']['stocks_max'],

        rsi_min = c['long']['rsi_min'],
        rsi_max = c['long']['rsi_max'],
        min_adx = c['long']['adx_min'],
        max_distance_sma200 = c['long']['distance_sma200_max'],
        max_volumen_relativo = c['long']['volume_rel_max'],
        min_performance_1y = c['long']['performance_min'],
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    setup_logging(args.verbose)

    config_file = Path(args.config)

    try:
        with config_file.open("rb") as f:
            c = tomllib.load(f)
    except FileNotFoundError:
        sys.exit(f"Error: no existe el archivo '{config_file}'.")
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"Error al leer '{config_file}': {e}")


    config = build_config(c)
    if args.show_earnings:
        config.days_min_earnings = 0

    finder = StocksFinder(config=config)
    candidates = finder.run()

    show_candidates(candidates)
    if args.output:
        export_candidates(candidates, args.output)


if __name__ == "__main__":
    main()
