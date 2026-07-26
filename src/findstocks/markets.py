"""Gestión de mercados: expansión de alias y validación contra tvscreener."""

from typing import Iterable, List, Union

EURONEXT = ["FRANCE", "NETHERLANDS", "BELGIUM", "PORTUGAL"]


def expand_markets(market: Union[str, Iterable[str]]) -> List[str]:
    """Normaliza la entrada a una lista de mercados en mayúsculas.

    "EURONEXT" se expande a sus países (Francia, Países Bajos, Bélgica,
    Portugal). Se eliminan duplicados manteniendo el orden de aparición.
    """
    entrada = [market] if isinstance(market, str) else list(market)

    markets: List[str] = []
    for m in entrada:
        if m.upper() == "EURONEXT":
            markets.extend(EURONEXT)
        else:
            markets.append(m.upper())

    return list(dict.fromkeys(markets))


def check_markets(markets: Iterable[str]) -> None:
    """Lanza ValueError si algún mercado no existe en tvscreener.Market."""
    import tvscreener as tvs

    for m in markets:
        if not hasattr(tvs.Market, m):
            disponibles = [d.name for d in tvs.Market]
            raise ValueError(f"Mercado '{m}' no existe. Disponibles: {disponibles}")
