"""
Screener de acciones para entrada en largo
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
import sys

# ---- Parametros ajustables ----
TOP_N_CAP = 50          # cuantas empresas de mayor capitalizacion evaluar
RSI_MIN, RSI_MAX = 35, 50  # zona de pullback sano
MIN_PERFORMANCE_1Y = 0.0   # rendimiento minimo a 1 ano (en %)
MAX_PRICE = 180   # filtra las que tienen un precio demasiado alto. Para desactivar el filtro poner valor 0.
MAX_STOCKS = 300  # maximo de stocks que va a coger de los markets (antes de filtrar)

def obtener_candidatos() -> pd.DataFrame:
    """Descarga el screener de Euronext (FR, NL, BE, PT) con los campos necesarios."""
    ss = tvs.StockScreener()
    ## print([m for m in dir(ss) if not m.startswith('_')])
    ss.set_range(0, MAX_STOCKS)
    ss.set_markets(
        tvs.Market.FRANCE,      # EURONEXT
        tvs.Market.NETHERLANDS, # EURONEXT    
        tvs.Market.BELGIUM,     # EURONEXT
        tvs.Market.PORTUGAL,    # EURONEXT   
        #tvs.Market.SPAIN,
        #tvs.Market.AMERICA,
        #tvs.Market.UK,
        #tvs.Market.JAPAN,
        #tvs.Market.GERMANY,
        #tvs.Market.CHINA,
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

    df = ss.get()
    #df = limpia_duplicados(df)
    return df


def limpia_duplicados(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quita las empresas duplicadas por cotizar en distintos exchanges
    """

    #df = df.sort_values("Market Capitalization", ascending=False)
    return df.drop_duplicates(subset="ISIN", keep="first")


def filtrar_candidatos(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica el filtro de gran capitalizacion + tendencia alcista + punto de entrada."""
    
    # filtra acciones demasiado caras
    if MAX_PRICE > 0:
        total = len(df)
        df = df[df["Price"] <= MAX_PRICE]
        print(f"\nDescartadas {total - len(df)} por tener un precio demasiado elevado.")

    # filtra las top capitalización
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
    print("Descargando tickers...")
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
        
        # convertimos el valor de capitalizacion a valores leíbles
        candidatos_final = candidatos[columnas_mostrar].copy()
        candidatos_final["Market Capitalization"] = (candidatos_final["Market Capitalization"] / 1_000_000_000).round(2).astype(str) + " B"

        print(candidatos_final.to_string(index=False))

    return candidatos


if __name__ == "__main__":
    args = sys.argv
    if len(args) > 1:
        if args[1] == "test":
            print([m.name for m in tvs.Market])
            sys.exit()
    main()