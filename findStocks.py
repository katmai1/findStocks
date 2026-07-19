"""
Screener de acciones para entrada en largo - Euronext, gran capitalizacion.

Criterios:
  - Alcista a largo plazo: precio > SMA200, y SMA50 > SMA200 (proxy de pendiente
    positiva de la SMA200, sin necesidad de historico propio)
  - Confirmacion anual: rendimiento a 1 ano > 0
  - Punto de entrada: RSI(14) en zona de pullback sano (35-50), ni sobrecomprado
    ni en caida libre
  - Universo: top N por capitalizacion de mercado dentro de Francia, Paises
    Bajos, Belgica y Portugal (Euronext no existe como mercado unico en
    TradingView, se combinan los paises)

Requisitos:
  pip install tvscreener pandas
"""

import tvscreener as tvs
from tvscreener import StockField
import pandas as pd

# ---- Parametros ajustables ----
TOP_N_CAP = 30          # cuantas empresas de mayor capitalizacion evaluar
RSI_MIN, RSI_MAX = 35, 50  # zona de pullback sano
MIN_PERFORMANCE_1Y = 0.0   # rendimiento minimo a 1 ano (en %)


def obtener_candidatos() -> pd.DataFrame:
    """Descarga el screener de Euronext (FR, NL, BE, PT) con los campos necesarios."""
    ss = tvs.StockScreener()

    ss.set_markets(
        tvs.Market.FRANCE,
        tvs.Market.NETHERLANDS,
        tvs.Market.BELGIUM,
        tvs.Market.PORTUGAL,
    )

    ss.specific_fields = [
        StockField.NAME,
        StockField.ISIN,
        StockField.PRICE,
        StockField.MARKET_CAPITALIZATION,
        StockField.RELATIVE_STRENGTH_INDEX_14,
        StockField.SIMPLE_MOVING_AVERAGE_50,
        StockField.SIMPLE_MOVING_AVERAGE_200,
        StockField.YEARLY_PERFORMANCE,
        StockField.EXCHANGE,
    ]

    return ss.get()


def filtrar_candidatos(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica el filtro de gran capitalizacion + tendencia alcista + punto de entrada."""
    df = df.sort_values("Market Capitalization", ascending=False).head(TOP_N_CAP)
    # print(list(df.columns))
    condiciones = (
        (df["Price"] > df["Simple Moving Average (200)"])
        & (df["Simple Moving Average (50)"] > df["Simple Moving Average (200)"])
        & (df["Yearly Performance"] > MIN_PERFORMANCE_1Y)
        & (df["Relative Strength Index (14)"].between(RSI_MIN, RSI_MAX))
    )

    return df[condiciones].copy()


def main():
    print("Descargando universo Euronext (FR, NL, BE, PT)...")
    df = obtener_candidatos()
    print(f"Total empresas obtenidas: {len(df)}")

    candidatos = filtrar_candidatos(df)

    columnas_mostrar = [
        "Name",
        "ISIN",
        "Exchange",
        "Price",
        "Market Capitalization",
        "Relative Strength Index (14)",
        "Simple Moving Average (50)",
        "Simple Moving Average (200)",
        "Yearly Performance",
    ]

    if candidatos.empty:
        print("\nNingun candidato cumple todos los criterios hoy.")
    else:
        print(f"\n{len(candidatos)} candidato(s) encontrados:\n")
        print(candidatos[columnas_mostrar].to_string(index=False))

    return candidatos


if __name__ == "__main__":
    main()