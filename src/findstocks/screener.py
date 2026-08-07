"""Lógica del screener: obtención de datos (I/O) y filtrado (puro).

`fetch_stocks` habla con TradingView vía tvscreener y por tanto necesita
red. `filter_candidates` es una función pura sobre un DataFrame y no
depende de red, lo que la hace fácil de testear.
"""

import logging
import math

import pandas as pd

from .config import ScreenerConfig
from .markets import check_markets

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
    #"Market Capitalization",
]

COLUMNAS_MOSTRAR = [
    "Direction",
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


def fetch_stocks(markets: list[str], max_stocks: int) -> pd.DataFrame:
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


def _condiciones_earnings(df: pd.DataFrame, condiciones_base: pd.Series, config: ScreenerConfig, etiqueta: str) -> pd.Series:
    """Calcula la condición de earnings y loguea cuántos candidatos descarta."""
    if config.days_min_earnings <= 0:
        return pd.Series(True, index=df.index)

    fecha_earnings = pd.to_datetime(df["Upcoming Earnings Date"], errors="coerce", utc=True)
    dias_hasta_earnings = (fecha_earnings - pd.Timestamp.now(tz="UTC")).dt.days
    # Solo descartamos si el earnings esta por venir dentro de la ventana (0 <= dias <= umbral).
    # Los earnings ya pasados (dias_hasta_earnings < 0) no deben descartar el candidato.
    c_earnings = (
        dias_hasta_earnings.isna()
        | (dias_hasta_earnings < 0)
        | (dias_hasta_earnings > config.days_min_earnings)
    )

    candidates = df[condiciones_base]
    descartados = len(candidates) - len(candidates[c_earnings.loc[candidates.index]])
    logger.info(f"[{etiqueta}] Descartados {descartados} candidatos por tener earnings en los proximos {config.days_min_earnings} días")
    return c_earnings


def _condiciones_long(df: pd.DataFrame, config: ScreenerConfig) -> pd.Series:
    """Tendencia alcista + pullback sano (RSI bajo dentro de la tendencia)."""
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

    c_earnings = _condiciones_earnings(df, condiciones_base, config, "LONG")
    return condiciones_base & c_earnings


def _condiciones_short(df: pd.DataFrame, config: ScreenerConfig) -> pd.Series:
    """Tendencia bajista + rebote hacia resistencia (RSI alto dentro de la tendencia)."""
    c_tendencia = df["Price"] < df["Simple Moving Average (200)"]
    c_tendencia_corto_plazo = df["Price"] < df["Simple Moving Average (50)"]
    c_pendiente = df["Simple Moving Average (50)"] < df["Simple Moving Average (200)"]
    c_performance = df["Yearly Performance"] < config.max_performance_1y_short
    c_rsi = df["Relative Strength Index (14)"].between(config.rsi_min_short, config.rsi_max_short)
    c_vol_rel = df["Relative Volume"] <= config.max_volumen_relativo_short
    c_valor_negociado = df["Volume*Price"] >= config.min_volume
    c_adx = df["Average Directional Index (14)"] > config.min_adx_short

    sma200 = df["Simple Moving Average (200)"].replace(0, pd.NA)
    # distancia por DEBAJO de la SMA200 (precio rebotando hacia la resistencia)
    distancia_sma200 = (sma200 - df["Price"]) / sma200
    c_distancia = distancia_sma200 <= config.max_distance_sma200_short

    condiciones_base = (
        c_tendencia
        & c_tendencia_corto_plazo   # test: sin esto encuentra posibles longs!!??
        & c_pendiente
        & c_performance
        & c_rsi
        & c_distancia
        & c_vol_rel
        & c_valor_negociado
        & c_adx
    )

    c_earnings = _condiciones_earnings(df, condiciones_base, config, "SHORT")
    return condiciones_base & c_earnings


def _preparar_universo(df: pd.DataFrame, config: ScreenerConfig) -> pd.DataFrame:
    """Limpieza común: datos completos, precio máximo, recorte por top% de capitalización."""
    antes = len(df)
    df = df.dropna(subset=COLUMNAS_REQUERIDAS)
    logger.info(f"Descartados {antes - len(df)} por datos incompletos.")

    if config.max_price > 0:
        total = len(df)
        df = df[df["Price"] <= config.max_price]
        logger.info(f"Descartadas {total - len(df)} por tener un precio demasiado elevado.")

    # filtra top%
    df = df.sort_values("Market Capitalization", ascending=False)
    antes_top = len(df)
    percent = config.top_n_cap / 100
    tamano_mercado = df.groupby("Market")["Market"].transform("size")
    n_por_mercado = (tamano_mercado * percent).apply(math.ceil).clip(lower=1)
    rango_en_mercado = df.groupby("Market").cumcount() + 1
    df = df[rango_en_mercado <= n_por_mercado]
    logger.info(f"Filtrando el {config.top_n_cap}% de las top: {antes_top} -> {len(df)}")

    return df


def filter_candidates(df: pd.DataFrame, config: ScreenerConfig) -> pd.DataFrame:
    """Aplica el filtro de gran capitalización + condiciones long y/o short
    según `config.long_enabled` / `config.short_enabled`. Función pura: no
    hace I/O, fácil de testear.

    El resultado incluye una columna "Direction" ("LONG" o "SHORT") para
    distinguir el tipo de candidato cuando ambos modos están activos.
    """
    df = _preparar_universo(df, config)

    resultados = []

    if config.long_enabled:
        candidatos_long = df[_condiciones_long(df, config)].copy()
        candidatos_long["Direction"] = "LONG"
        resultados.append(candidatos_long)

    if config.short_enabled:
        candidatos_short = df[_condiciones_short(df, config)].copy()
        candidatos_short["Direction"] = "SHORT"
        resultados.append(candidatos_short)

    if not resultados:
        vacio = df.iloc[0:0].copy()
        vacio["Direction"] = pd.Series(dtype="object")
        return vacio

    return pd.concat(resultados)


class StocksFinder:
    """Orquesta obtención + filtrado para uno o varios mercados."""

    def __init__(self, config):
        
        self.config = config
        check_markets(self.config.markets)
        self.stocks: pd.DataFrame | None = None
        self.candidates: pd.DataFrame | None = None

    def run(self) -> pd.DataFrame:
        self.stocks = fetch_stocks(self.config.markets, self.config.max_stocks)
        self.candidates = filter_candidates(self.stocks, self.config)
        return self.candidates
