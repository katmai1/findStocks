"""Gestión de mercados: expansión de alias y validación contra tvscreener."""

from typing import Iterable


def check_markets(markets: Iterable[str]) -> None:
    """Lanza ValueError si algún mercado no existe en tvscreener.Market."""
    import tvscreener as tvs

    for m in markets:
        if not hasattr(tvs.Market, m):
            disponibles = [d.name for d in tvs.Market]
            raise ValueError(f"Mercado '{m}' no existe. Disponibles: {disponibles}")
