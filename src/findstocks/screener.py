"""Lógica del screener: obtención de datos (I/O) y filtrado (puro).

`fetch_stocks` habla con TradingView vía tvscreener y por tanto necesita
red. `filter_candidates` es una función pura sobre un DataFrame y no
depende de red, lo que la hace fácil de testear.
"""

import math
import logging
from typing import List, Optional

import pandas as pd

from .config import ScreenerConfig
from .markets import check_markets, expand_markets

logger = logging.getLogger(__name__)

# campos solicitados al screener de TradingView
CAMPOS_TV = [
    "NAME",
    "ISIN",
    "PRICE",
    "MARKET_CAPITALIZATION",
    "RELATIVE_STRENGTH_INDEX_14",
    "AVERAGE_DIRECTIONAL_INDEX_14",
    "SIMPLE_MOVING_AVERAGE_50",
    "SIMPLE_MOVING_AVERAGE_200",
    "YEARLY_PERFORMANCE",
    "EXCHANGE",
    "RELATIVE_VOLUME",
    "VOLUMEXPRICE",
    "UPCOMING_EARNINGS_DATE",
]

COLUMNAS_REQUERIDAS = [
    "Price",
    "Simple Moving Average (50)",
    "Simple Moving Average (200)",
    "Relative Strength Index (14)",
    "Average Directional Index (14)",
]

COLUMNAS_MOSTRAR = [
    "ISIN",
    "Name",
    "Market",
    "Exchange",
    "Price",
    "Market Capitalization",
    "Relative Strength Index (14)",
    "Volume*Price",
    "Relative Volume",
]


def _get_stock_fields():
    """Resuelve los StockField reales de tvscreener (importado en diferido
    para que este módulo se pueda testear sin la librería instalada, salvo
    cuando se llama a fetch_stocks)."""
    import tvscreener as tvs

    return [getattr(tvs.StockField, nombre) for nombre in CAMPOS_TV]


def fetch_stocks(markets: List[str], max_stocks: int) -> pd.DataFrame:
    """Descarga la lista completa de stocks para los mercados dados.

    Requiere red (llama a la API de TradingView vía tvscreener).
    """
    import tvscreener as tvs

    campos = _get_stock_fields()
    frames = []
    for market in markets:
        ss_market = tvs.StockScreener()
        ss_market.set_range(0, max_stocks)
        ss_market.set_markets(getattr(tvs.Market, market))
        ss_market.specific_fields = campos

        try:
            df_market = ss_market.get()
            df_market["Market"] = market
            logger.info(f"{market}: {len(df_market)} stocks")
            frames.append(df_market)
        except Exception:
            logger.exception(f"Error obteniendo {market}")
            continue

    if not frames:
        raise RuntimeError("No se obtenieron datos de ningun mercado")

    df = pd.concat(frames, ignore_index=True)
    logger.info(f"Obtenidos un total de {len(df)} stocks")
    return df


def filter_candidates(df: pd.DataFrame, config: ScreenerConfig) -> pd.DataFrame:
    """Aplica el filtro de gran capitalización + tendencia alcista + punto
    de entrada. Función pura: no hace I/O, fácil de testear.
    """
    antes = len(df)
    df = df.dropna(subset=COLUMNAS_REQUERIDAS)
    logger.info(f"Descartados {antes - len(df)} por datos incompletos.")

    if config.max_price > 0:
        total = len(df)
        df = df[df["Price"] <= config.max_price]
        logger.info(f"Descartadas {total - len(df)} por tener un precio demasiado elevado.")

    # filtra top%
    antes_top = len(df)
    percent = config.top_n_cap / 100
    def _cabeza_pct(grupo: pd.DataFrame) -> pd.DataFrame:
        n = max(1, math.ceil(len(grupo) * percent))
        return grupo.head(n)
    df = df.groupby("Market", group_keys=False).apply(_cabeza_pct)
    logger.info(f"Aplicado top_pct={config.top_n_cap}%: {antes_top} -> {len(df)}")
    # df = (
    #     df.sort_values("Market Capitalization", ascending=False)
    #     .groupby("Market", group_keys=False)
    #     .head(config.top_n_cap)
    # )

    c_tendencia = df["Price"] > df["Simple Moving Average (200)"]
    c_pendiente = df["Simple Moving Average (50)"] > df["Simple Moving Average (200)"]
    c_performance = df["Yearly Performance"] > config.min_performance_1y
    c_rsi = df["Relative Strength Index (14)"].between(config.rsi_min, config.rsi_max)
    c_vol_rel = df["Relative Volume"] <= config.max_volumen_relativo
    c_valor_negociado = df["Volume*Price"] >= config.min_volume
    c_adx = df["Average Directional Index (14)"] > config.min_adx

    sma200 = df["Simple Moving Average (200)"].replace(0, pd.NA)
    distancia_sma200 = (df["Price"] - sma200) / sma200
    c_distancia = distancia_sma200 <= config.max_distance_sma200


    condiciones_base = (
        c_tendencia
        & c_pendiente
        & c_performance
        & c_rsi
        & c_distancia
        & c_vol_rel
        & c_valor_negociado
        & c_adx
    )

    if config.days_min_earnings > 0:
        fecha_earnings = pd.to_datetime(df["Upcoming Earnings Date"], errors="coerce", utc=True)
        dias_hasta_earnings = (fecha_earnings - pd.Timestamp.now(tz="UTC")).dt.days
        c_earnings = dias_hasta_earnings.isna() | (dias_hasta_earnings > config.days_min_earnings)
        candidates = df[condiciones_base]
        candidates_earnings = len(candidates) - len(candidates[c_earnings.loc[candidates.index]])
        logger.info(f"Descartados {candidates_earnings} candidatos por tener earnings en los proximos {config.days_min_earnings} días")
    else:
        c_earnings = pd.Series(True, index=df.index)

    condiciones = condiciones_base & c_earnings
    return df[condiciones].copy()


class StocksFinder:
    """Orquesta obtención + filtrado para uno o varios mercados."""

    def __init__(self, market="EURONEXT", config: Optional[ScreenerConfig] = None):
        self.markets = expand_markets(market)
        check_markets(self.markets)
        self.config = config or ScreenerConfig()
        self.stocks: Optional[pd.DataFrame] = None
        self.candidates: Optional[pd.DataFrame] = None

    def run(self) -> pd.DataFrame:
        self.stocks = fetch_stocks(self.markets, self.config.max_stocks)
        self.candidates = filter_candidates(self.stocks, self.config)
        return self.candidates
