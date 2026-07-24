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

import argparse
import tvscreener as tvs
from tvscreener import StockField
import pandas as pd
import sys


class StocksFinder:

    # markets
    euronext = ["FRANCE", "NETHERLANDS", "BELGIUM", "PORTUGAL"]
    markets = []
    # options
    TOP_N_CAP = 30
    RSI_MIN, RSI_MAX = 35, 50  # zona de pullback sano
    MIN_PERFORMANCE_1Y = 0.0   # rendimiento minimo a 1 ano (en %)
    MAX_PRICE = 180   # descarta las que tienen un precio demasiado alto. Para desactivar el filtro poner valor 0.
    MAX_STOCKS = 300  # maximo de stocks que va a coger de los markets (antes de filtrar)
    MAX_DISTANCIA_SMA200 = 0.15 # descarta los que estan demasiado sobreextendidos
    MAX_VOLUMEN_RELATIVO = 1.0 # descarta los que aumentaron su volumen durente la corrección
    MIN_VOLUME = 100_000  # volumen medio diario minimo
    MIN_ADX = 20  # ADX(14) minimo para descartar mercados laterales sin tendencia clara 

    def __init__(self, market="EURONEXT"):        
        # normaliza a lista, sea cual sea la entrada (str suelto o lista)
        if isinstance(market, str):
            entrada = [market]
        else:
            entrada = list(market)
 
        # expande la palabra clave "euronext" a sus paises, y deja el resto tal cual
        self.markets = []
        for m in entrada:
            if m.upper() == "EURONEXT":
                self.markets.extend(self.euronext)
            else:
                self.markets.append(m.upper())
 
        # quita duplicados manteniendo el orden (ej. si pasas "euronext" y "france" a la vez)
        self.markets = list(dict.fromkeys(self.markets))
        
        # check markets
        self.checkMarkets()

    def run(self):
        # obtiene lista completa de stocks
        self.stocks = self.getStocks()
        # filtra los candidatos q cumplan todos los criterios
        self.candidates = self.getCandidates()
        # muestra los resultados
        self.showCandidates()

    def checkMarkets(self):
        for m in self.markets:
            if not hasattr(tvs.Market, m):
                disponibles = [d.name for d in tvs.Market]
                raise ValueError(f"Mercado '{m}' no existe. Disponibles: {disponibles}")

    def getStocks(self) -> pd.DataFrame:
        """Devuelva la lista completa de stocks"""
        campos = [
            StockField.NAME,
            StockField.ISIN,
            StockField.PRICE,
            StockField.MARKET_CAPITALIZATION,
            StockField.RELATIVE_STRENGTH_INDEX_14,
            StockField.AVERAGE_DIRECTIONAL_INDEX_14,
            StockField.SIMPLE_MOVING_AVERAGE_50,
            StockField.SIMPLE_MOVING_AVERAGE_200,
            StockField.YEARLY_PERFORMANCE,
            StockField.EXCHANGE,
            StockField.RELATIVE_VOLUME,
            StockField.VOLUMEXPRICE,
        ]
        frames = []
        for market in self.markets:
            ss_market = tvs.StockScreener()
            ss_market.set_range(0, self.MAX_STOCKS)
            ss_market.set_markets(getattr(tvs.Market, market))
            ss_market.specific_fields = campos

            try:
                df_market = ss_market.get()
                df_market["Market"] = market
                print(f"\n{market}: {len(df_market)} stocks")
                frames.append(df_market)
            except Exception as e:
                print(f"Error obteniendo {market}: {e}")
                continue
            
        
        df = pd.concat(frames, ignore_index=True)
        # filtrar duplicados?
        print(f"\nObtenidos un total de {len(df)} stocks")
        return df

    def getCandidates(self) -> pd.DataFrame:
        """Aplica el filtro de gran capitalizacion + tendencia alcista + punto de entrada."""
        
        df = self.stocks

        # descarta los q tengan valores NA
        antes = len(df)
        df = df.dropna(subset=[
            "Price", "Simple Moving Average (50)", "Simple Moving Average (200)",
            "Relative Strength Index (14)", "Average Directional Index (14)"
            ])
        print(f"Descartados {antes - len(df)} por datos incompletos.")

        # descarta acciones demasiado caras
        if self.MAX_PRICE > 0:
            total = len(df)
            df = df[df["Price"] <= self.MAX_PRICE]
            print(f"\nDescartadas {total - len(df)} por tener un precio demasiado elevado.")

        # filtra las top capitalización x mercado
        df = (df.sort_values("Market Capitalization", ascending=False).groupby("Market", group_keys=False).head(self.TOP_N_CAP))

        # condiciones tecnicas
        c_tendencia = df["Price"] > df["Simple Moving Average (200)"]
        c_pendiente = df["Simple Moving Average (50)"] > df["Simple Moving Average (200)"]
        c_performance = df["Yearly Performance"] > self.MIN_PERFORMANCE_1Y
        c_rsi = df["Relative Strength Index (14)"].between(self.RSI_MIN, self.RSI_MAX)
        c_vol_rel = df["Relative Volume"] <= self.MAX_VOLUMEN_RELATIVO
        c_valor_negociado = df["Volume*Price"] >= self.MIN_VOLUME
        c_adx = df["Average Directional Index (14)"] > self.MIN_ADX
        
        # condicion distancia a sma200
        sma200 = df["Simple Moving Average (200)"].replace(0, pd.NA)    # filtra errores
        distancia_sma200 = (df["Price"] - sma200) / sma200
        c_distancia = distancia_sma200 <= self.MAX_DISTANCIA_SMA200

        condiciones = (
            c_tendencia             # check tendencia alcista
            & c_pendiente           # check que la sma corta esté por encima de la larga
            & c_performance         # check positivo en el ultimo año
            & c_rsi                 # check RSI entre 35-50, por ser una zona de pullback sano
            & c_distancia           # check que no esté sobreextendida, descartando las que estan demasiado alejadas del sma200
            & c_vol_rel             # check volumen relativo a los 10 ultimos dias, para descartar las que tengan fuertes ventas
            & c_valor_negociado     # check acciones con valor demasiado poco volumen (en divisa)
            & c_adx                 # check ADX(14) > MIN_ADX, para descartar rangos laterales sin tendencia clara
        )

        return df[condiciones].copy()

    def showCandidates(self):
        """Muestra los candidatos en pantalla"""
        columnas_mostrar = [
        "ISIN",
        "Name",
        "Market",
        "Exchange",
        "Price",
        "Market Capitalization",
        "Relative Strength Index (14)",
        # "Average Directional Index (14)",
        # "Simple Moving Average (50)",
        # "Simple Moving Average (200)",
        #"Yearly Performance",
        "Volume*Price",
        "Relative Volume",
        ]

        if self.candidates.empty:
            print("\nNingun candidato cumple todos los criterios hoy.")
        else:
            print(f"\n{len(self.candidates)} candidato(s) encontrados:\n")
            
            # convertimos el valor de capitalizacion a valores leíbles
            candidatos_final = self.candidates[columnas_mostrar].copy()
            candidatos_final["Market Capitalization"] = (candidatos_final["Market Capitalization"] / 1_000_000_000).round(2).astype(str) + " B"

            print(candidatos_final.to_string(index=False))


def parse_args():
    parser = argparse.ArgumentParser(description="Script para encontrar entradas en largo en acciones")
    parser.add_argument(
        "-m", "--market",
        nargs="*",
        default="EURONEXT",
        help="Mercado para analizar. Ex: EURONEXT, AMERICA, GERMANY..."
    )

    parser.add_argument(
        "-t", "--top",
        type=int,
        default=30,
        help="Top de empresas por capitalización. Default: 20"
    )

    args = parser.parse_args()
    if not args.market:
        parser.error("--market requiere al menos un valor (ej: -m EURONEXT FRANCE)")
    return args

if __name__ == "__main__":
    args = parse_args()

    sf = StocksFinder(market=args.market)
    sf.TOP_N_CAP = args.top
    sf.run()
