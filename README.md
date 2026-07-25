# findStocks

Screener de acciones en Python que busca valores en **fase de pullback dentro de una tendencia alcista**, usando datos de TradingView a través de la librería [`tvscreener`](https://pypi.org/project/tvscreener/).

La idea es encontrar acciones que:
1. Están en tendencia alcista de fondo (largo plazo).
2. Han corregido un poco (pullback sano, sin estar en caída libre ni sobrecompradas).
3. Tienen liquidez suficiente y no publican resultados (earnings) en los próximos días.

## Criterios de selección

- **Tendencia alcista a largo plazo**: precio > SMA(200) y SMA(50) > SMA(200) (esto último se usa como proxy de que la SMA200 tiene pendiente positiva, sin necesitar histórico propio).
- **Confirmación anual**: rendimiento a 1 año > 0%.
- **Punto de entrada (pullback)**: RSI(14) entre 35 y 50 — ni sobrecomprado ni en caída libre.
- **Fuerza de tendencia**: ADX(14) por encima de un mínimo, para descartar mercados laterales sin tendencia clara.
- **No sobreextendida**: distancia entre el precio y la SMA(200) por debajo de un máximo.
- **Volumen relativo bajo**: descarta acciones cuyo volumen ha aumentado fuerte durante la corrección (señal de ventas de pánico).
- **Liquidez mínima**: volumen medio diario (en valor) por encima de un mínimo.
- **Sin earnings inminentes**: descarta acciones con resultados dentro de los próximos N días (configurable, o desactivable).
- **Filtro de precio máximo** y **top N por capitalización** por mercado (desactivables).

## Instalar requisitos

```bash
python3 -m venv .venv
source .venv/bin/activate       # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
python3 findStocks.py [opciones]
```

Ejemplos:

```bash
# Por defecto analiza EURONEXT (Francia, Países Bajos, Bélgica, Portugal)
python3 findStocks.py

# Analizar varios mercados a la vez
python3 findStocks.py -m FRANCE GERMANY AMERICA

# Ajustar la zona de RSI de pullback y el precio máximo
python3 findStocks.py --rsi-min 30 --rsi-max 45 --max-price 250

# Top 50 por capitalización y logs detallados
python3 findStocks.py -t 50 -v

# Incluir candidatos aunque tengan earnings próximos
python3 findStocks.py -e
```

### Opciones disponibles

| Opción | Descripción | Valor por defecto |
|---|---|---|
| `-m`, `--market` | Mercado(s) a analizar (ej. `EURONEXT`, `FRANCE`, `AMERICA`, `GERMANY`...). `EURONEXT` se expande automáticamente a Francia, Países Bajos, Bélgica y Portugal. | `EURONEXT` |
| `-t`, `--top` | Top de empresas por capitalización a considerar por mercado. | `30` |
| `-e`, `--earnings` | Muestra candidatos aunque tengan earnings próximos (desactiva ese filtro). | Desactivado |
| `--rsi-min` | RSI mínimo de la zona de pullback. | `35` |
| `--rsi-max` | RSI máximo de la zona de pullback. | `50` |
| `--max-price` | Precio máximo del valor (`0` para desactivar el filtro). | `180` |
| `-v`, `--verbose` | Muestra logs detallados (nivel debug). | Desactivado |

## Salida

El script imprime por consola una tabla con los candidatos encontrados, incluyendo ISIN, nombre, mercado, exchange, precio, capitalización, RSI(14), volumen en valor y volumen relativo. Si ningún valor cumple los criterios ese día, se informa por log.

## Requisitos

- Python 3.8+
- `pandas`
- `tvscreener`

## Aviso

Esta herramienta es solo para fines informativos/educativos y **no constituye asesoramiento financiero**. Verifica siempre los datos y realiza tu propio análisis antes de tomar decisiones de inversión.
