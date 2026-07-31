"""Configuración de umbrales del screener.

Todos los valores tienen un default razonable pero pueden sobreescribirse
por CLI (ver cli.py) o instanciando ScreenerConfig directamente.
"""

from dataclasses import dataclass, field


@dataclass
class ScreenerConfig:
    
    markets: list[str] = field(default_factory=list)
    long_enabled: bool = True
    short_enabled: bool = False

    # nº de empresas top por capitalización a considerar, por mercado
    top_n_cap: int = 30

    # zona de RSI(14) considerada "pullback sano"
    rsi_min: int = 35
    rsi_max: int = 50

    # rendimiento minimo a 1 año (en %)
    min_performance_1y: float = 0.0

    # descarta acciones con precio > max_price. 0 para desactivar el filtro.
    max_price: float = 180

    # maximo de stocks que se piden a cada mercado (antes de filtrar)
    max_stocks: int = 500

    # descarta las que estan demasiado sobreextendidas respecto a la SMA200
    max_distance_sma200: float = 0.15

    # descarta las que aumentaron mucho su volumen durante la corrección
    max_volumen_relativo: float = 1.0

    # volumen medio diario minimo (en valor, no en nº de acciones)
    min_volume: int = 30_000

    # ADX(14) minimo, para descartar mercados laterales sin tendencia clara
    min_adx: int = 20

    # descarta acciones con earnings dentro de N dias. 0 para desactivar.
    days_min_earnings: int = 15
