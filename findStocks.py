"""
Screener de acciones para entrada en largo
Criterios:
  - Alcista a largo plazo: precio > SMA200, y SMA50 > SMA200 (proxy de pendiente
    positiva de la SMA200, sin necesidad de historico propio)
  - Confirmacion anual: rendimiento a 1 ano > 0
  - Punto de entrada: RSI(14) en zona de pullback sano (35-50), ni sobrecomprado
    ni en caida libre

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



class StocksFinder:

    ss = tvs.StockScreener()
    euronext = ["FRANCE", "NETHERLANDS", "BELGIUM", "PORTUGAL"]
    markets = []

    def __init__(self, market="EURONEXT", TOTAL_STOCKS=300):
        self.ss.set_range(0, TOTAL_STOCKS)
        
        # set markets
        if market.upper() == "EURONEXT":
            self.markets = self.euronext
        else:
            self.markets.append(market.upper())
        self.setMarkets()

        # get stocks
        self.stocks = self.getStocks()
        
        # filter stocks
        self.candidates = self.getCandidates()
        
        # show results
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

        if self.candidates.empty:
            print("\nNingun candidato cumple todos los criterios hoy.")
        else:
            print(f"\n{len(self.candidates)} candidato(s) encontrados:\n")
            
            # convertimos el valor de capitalizacion a valores leíbles
            candidatos_final = self.candidates[columnas_mostrar].copy()
            candidatos_final["Market Capitalization"] = (candidatos_final["Market Capitalization"] / 1_000_000_000).round(2).astype(str) + " B"

            print(candidatos_final.to_string(index=False))

    def setMarkets(self):
        """Carga la lista de markets y la setea al screener"""
        mlist = []
        for m in self.markets:
            if not hasattr(tvs.Market, m):
                disponibles = [d.name for d in tvs.Market]
                raise ValueError(f"Mercado '{m}' no existe. Disponibles: {disponibles}")
            mlist.append(getattr(tvs.Market, m))
        self.ss.set_markets(*mlist)
    
    def getStocks(self) -> pd.DataFrame:
        """Devuelva la lista completa de stocks"""
        self.ss.specific_fields = [
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
        df = self.ss.get()
        # filtrar duplicados?
        return df

    def getCandidates(self) -> pd.DataFrame:
        """Aplica el filtro de gran capitalizacion + tendencia alcista + punto de entrada."""
        
        df = self.stocks
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


# def limpia_duplicados(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Quita las empresas duplicadas por cotizar en distintos exchanges
#     """

#     #df = df.sort_values("Market Capitalization", ascending=False)
#     return df.drop_duplicates(subset="ISIN", keep="first")


if __name__ == "__main__":
    args = sys.argv
    if len(args) > 1:
        if args[1] == "test":
            print([m.name for m in tvs.Market])
            sys.exit()
    sf = StocksFinder(market="FRANCE")
