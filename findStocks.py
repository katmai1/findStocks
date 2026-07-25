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

import logging
import argparse
import tvscreener as tvs
from tvscreener import StockField
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class StocksFinder:

    # campos obtenidos por el screener
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
        StockField.UPCOMING_EARNINGS_DATE,
    ]
    # markets
    euronext = ["FRANCE", "NETHERLANDS", "BELGIUM", "PORTUGAL"]
    markets = []
    # options
    TOP_N_CAP = 30
    RSI_MIN, RSI_MAX = 35, 50  # zona de pullback sano
    MIN_PERFORMANCE_1Y = 0.0   # rendimiento minimo a 1 ano (en %)
    MAX_PRICE = 180   # descarta las que tienen un precio demasiado alto. Para desactivar el filtro poner valor 0.
    MAX_STOCKS = 500  # maximo de stocks que va a coger de los markets (antes de filtrar)
    MAX_DISTANCE_SMA200 = 0.15 # descarta los que estan demasiado sobreextendidos
    MAX_VOLUMEN_RELATIVO = 1.0 # descarta los que aumentaron su volumen durente la corrección
    MIN_VOLUME = 30_000  # volumen medio diario minimo
    MIN_ADX = 20  # ADX(14) minimo para descartar mercados laterales sin tendencia clara
    DAYS_MIN_EARNINGS = 15      # descarta acciones con earnings dentro de N dias. Para desactivar poner valor 0.

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
        frames = []
        for market in self.markets:
            ss_market = tvs.StockScreener()
            ss_market.set_range(0, self.MAX_STOCKS)
            ss_market.set_markets(getattr(tvs.Market, market))
            ss_market.specific_fields = self.campos

            try:
                df_market = ss_market.get()
                df_market["Market"] = market
                logger.info(f"{market}: {len(df_market)} stocks")
                frames.append(df_market)
            except Exception as e:
                logger.error(f"Error obteniendo {market}")
                continue
            
        if not frames:
            raise RuntimeError("No se obtenieron datos de ningun mercado")
        df = pd.concat(frames, ignore_index=True)
        # filtrar duplicados?
        logger.info(f"Obtenidos un total de {len(df)} stocks")
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
        logger.info(f"Descartados {antes - len(df)} por datos incompletos.")

        # descarta acciones demasiado caras
        if self.MAX_PRICE > 0:
            total = len(df)
            df = df[df["Price"] <= self.MAX_PRICE]
            logger.info(f"Descartadas {total - len(df)} por tener un precio demasiado elevado.")

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
        c_distancia = distancia_sma200 <= self.MAX_DISTANCE_SMA200
        # condicion earnings
        if self.DAYS_MIN_EARNINGS > 0:
            fecha_earnings = pd.to_datetime(df["Upcoming Earnings Date"], errors="coerce", utc=True)
            dias_hasta_earnings = (fecha_earnings - pd.Timestamp.now(tz="UTC")).dt.days
            c_earnings = dias_hasta_earnings.isna() | (dias_hasta_earnings > self.DAYS_MIN_EARNINGS)
        else:
            c_earnings = pd.Series(True, index=df.index)

        condiciones_base = (
            c_tendencia             # check tendencia alcista
            & c_pendiente           # check que la sma corta esté por encima de la larga
            & c_performance         # check positivo en el ultimo año
            & c_rsi                 # check RSI entre 35-50, por ser una zona de pullback sano
            & c_distancia           # check que no esté sobreextendida, descartando las que estan demasiado alejadas del sma200
            & c_vol_rel             # check volumen relativo a los 10 ultimos dias, para descartar las que tengan fuertes ventas
            & c_valor_negociado     # check acciones con valor demasiado poco volumen (en divisa)
            & c_adx                 # check ADX(14) > MIN_ADX, para descartar rangos laterales sin tendencia clara
        )
        # cuenta los earnings
        candidates = df[condiciones_base]
        candidates_earnings = len(candidates) - len(candidates[c_earnings.loc[candidates.index]])
        logger.info(f"Descartados {candidates_earnings} candidatos por tener earnings en los proximos {self.DAYS_MIN_EARNINGS} días")

        condiciones = condiciones_base & c_earnings

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
            logger.info("Ningun candidato cumple todos los criterios hoy.")
        else:
            print(f"\n Encontrado(s) {len(self.candidates)} candidato(s):\n")
            
            # convertimos el valor de capitalizacion a valores leíbles
            candidatos_final = self.candidates[columnas_mostrar].copy()
            candidatos_final["Market Capitalization"] = (candidatos_final["Market Capitalization"] / 1_000_000_000).round(2).astype(str) + " B"

            print(candidatos_final.to_string(index=False))

#####################
### OPTIONS

def parse_args():
    parser = argparse.ArgumentParser(description="Script para encontrar entradas en largo en acciones")
    # options
    parser.add_argument(
        "-m", "--market",
        nargs="*",
        default=["EURONEXT"],
        help="Mercado para analizar. Ex: EURONEXT, AMERICA, GERMANY..."
    )

    parser.add_argument(
        "-t", "--top",
        type=int,
        default=30,
        help="Top de empresas por capitalización. Default: 20"
    )

    parser.add_argument("-e", "--earnings", help="Muestra candidatos aunque haya 'earnings' cerca.", action="store_true")
    parser.add_argument("--rsi-min", type=int, default=35, help="RSI mínimo de la zona de pullback")
    parser.add_argument("--rsi-max", type=int, default=50, help="RSI máximo de la zona de pullback")
    parser.add_argument("--max-price", type=float, default=180, help="Precio máximo (0 para desactivar)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Muestra logs detallados (debug)")
    # -----------
    args = parser.parse_args()
    if not args.market:
        parser.error("--market requiere al menos un valor (ej: -m EURONEXT FRANCE)")
    return args

###################
### LOGGING

def setup_logging(verbose=False):
    nivel = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


### MAIN
if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)

    sf = StocksFinder(market=args.market)

    sf.TOP_N_CAP = args.top
    sf.RSI_MIN = args.rsi_min
    sf.RSI_MAX = args.rsi_max
    sf.MAX_PRICE = args.max_price
    if args.earnings:
        sf.DAYS_MIN_EARNINGS = 0
    
    sf.run()
