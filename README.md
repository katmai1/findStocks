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

## Estructura del proyecto

```
findStocks/
├── src/findstocks/
│   ├── config.py          # umbrales del screener (ScreenerConfig)
│   ├── markets.py         # expansión/validación de mercados
│   ├── screener.py        # obtención de datos + filtrado (lógica pura testeable)
│   ├── output.py          # presentación en consola y export a CSV/XLSX
│   ├── cli.py              # parseo de argumentos y orquestación
│   └── logging_setup.py
├── tests/                  # tests unitarios (pytest)
├── main.py                 # punto de entrada
└── pyproject.toml
```

## Instalar requisitos

Opción rápida (solo ejecutar el script):

```bash
python3 -m venv .venv
source .venv/bin/activate       # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Opción recomendada (instala el paquete y el comando `findstocks`, incluye deps de test/lint):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Uso

```bash
python3 main.py [opciones]
# o, si instalaste con pip install -e ".[dev]":
findstocks [opciones]
```

Ejemplos:

```bash
# Por defecto analiza EURONEXT (Francia, Países Bajos, Bélgica, Portugal)
python3 main.py

# Analizar varios mercados a la vez
python3 main.py -m FRANCE GERMANY AMERICA

# Ajustar la zona de RSI de pullback y el precio máximo
python3 main.py --rsi-min 30 --rsi-max 45 --max-price 250

# Top 50 por capitalización y logs detallados
python3 main.py -t 50 -v

# Incluir candidatos aunque tengan earnings próximos
python3 main.py -e

# Exportar resultados a CSV
python3 main.py -o candidatos.csv
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
| `--min-adx` | ADX(14) mínimo. | `20` |
| `--max-distance-sma200` | Distancia máxima al SMA200 (proporción). | `0.15` |
| `--min-volume` | Volumen medio diario mínimo (en valor). | `30000` |
| `--earnings-days` | Días mínimos hasta earnings para no descartar. | `15` |
| `-o`, `--output` | Exporta los resultados a un archivo `.csv` o `.xlsx`. | Sin exportar |
| `-v`, `--verbose` | Muestra logs detallados (nivel debug). | Desactivado |

## Salida

El script imprime por consola una tabla con los candidatos encontrados, incluyendo ISIN, nombre, mercado, exchange, precio, capitalización, RSI(14), volumen en valor y volumen relativo. Si ningún valor cumple los criterios ese día, se informa por log.

## Tests

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Los tests cubren la lógica de filtrado (`findstocks.screener.filter_candidates`) y
la expansión de mercados (`findstocks.markets`), sin necesidad de red. En cada push
se ejecutan automáticamente vía GitHub Actions (`.github/workflows/ci.yml`).

## Requisitos

- Python 3.8+
- `pandas`
- `tvscreener`

## Aviso

Esta herramienta es solo para fines informativos/educativos y **no constituye asesoramiento financiero**. Verifica siempre los datos y realiza tu propio análisis antes de tomar decisiones de inversión.
