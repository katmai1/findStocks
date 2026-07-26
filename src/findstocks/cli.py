"""Interfaz de línea de comandos."""

import argparse
from typing import Optional, Sequence

from .config import ScreenerConfig
from .logging_setup import setup_logging
from .output import export_candidates, show_candidates
from .screener import StocksFinder


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Script para encontrar entradas en largo en acciones")

    parser.add_argument(
        "-m", "--market",
        nargs="*",
        default=["EURONEXT"],
        help="Mercado(s) para analizar. Ex: EURONEXT, AMERICA, GERMANY...",
    )
    parser.add_argument(
        "-t", "--top",
        type=int,
        default=30,
        help="Top de empresas por capitalización. Default: 30",
    )
    parser.add_argument(
        "-e", "--earnings",
        action="store_true",
        help="Muestra candidatos aunque haya 'earnings' cerca (desactiva ese filtro).",
    )
    parser.add_argument("--rsi-min", type=int, default=35, help="RSI mínimo de la zona de pullback")
    parser.add_argument("--rsi-max", type=int, default=50, help="RSI máximo de la zona de pullback")
    parser.add_argument("--max-price", type=float, default=180, help="Precio máximo (0 para desactivar)")
    parser.add_argument("--min-adx", type=int, default=20, help="ADX(14) mínimo")
    parser.add_argument(
        "--max-distance-sma200", type=float, default=0.15,
        help="Distancia máxima al SMA200 (proporción, ej. 0.15 = 15%%)",
    )
    parser.add_argument(
        "--min-volume", type=int, default=30_000,
        help="Volumen medio diario mínimo, en valor (no en nº de acciones)",
    )
    parser.add_argument(
        "--earnings-days", type=int, default=15,
        help="Días mínimos hasta earnings para no descartar (0 para desactivar el filtro)",
    )
    parser.add_argument("-o", "--output", help="Exporta los resultados a un archivo CSV o XLSX")
    parser.add_argument("-v", "--verbose", action="store_true", help="Muestra logs detallados (debug)")

    args = parser.parse_args(argv)
    if not args.market:
        parser.error("--market requiere al menos un valor (ej: -m EURONEXT FRANCE)")
    return args


def build_config(args: argparse.Namespace) -> ScreenerConfig:
    return ScreenerConfig(
        top_n_cap=args.top,
        rsi_min=args.rsi_min,
        rsi_max=args.rsi_max,
        max_price=args.max_price,
        min_adx=args.min_adx,
        max_distance_sma200=args.max_distance_sma200,
        min_volume=args.min_volume,
        days_min_earnings=0 if args.earnings else args.earnings_days,
    )


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    setup_logging(args.verbose)

    config = build_config(args)
    finder = StocksFinder(market=args.market, config=config)
    candidates = finder.run()

    show_candidates(candidates)
    if args.output:
        export_candidates(candidates, args.output)


if __name__ == "__main__":
    main()
