# findStocks

Screener de acciones en Python que busca valores en **fase de pullback dentro de una tendencia alcista**, usando datos de TradingView a través de la librería [`tvscreener`](https://pypi.org/project/tvscreener/).

La idea es encontrar acciones que:
1. Están en tendencia alcista de fondo (largo plazo).
2. Han corregido un poco (pullback sano, sin estar en caída libre ni sobrecompradas).
3. Tienen liquidez suficiente y no publican resultados (earnings) en los próximos días.

Es la primera fase de un proceso manual: el script reduce un universo grande de acciones a una lista corta, y luego cada candidato se revisa a mano en el gráfico antes de tomar cualquier decisión.

## Criterios de selección (modo long)

- **Tendencia alcista a largo plazo**: precio > SMA(200) y SMA(50) > SMA(200) (esto último se usa como proxy de que la SMA200 tiene pendiente positiva, sin necesitar histórico propio).
- **Confirmación anual**: rendimiento a 1 año > 0%.
- **Punto de entrada (pullback)**: RSI(14) entre `rsi_min` y `rsi_max` — ni sobrecomprado ni en caída libre.
- **Fuerza de tendencia**: ADX(14) por encima de un mínimo, para descartar mercados laterales sin tendencia clara.
- **No sobreextendida**: distancia entre el precio y la SMA(200) por debajo de un máximo.
- **Volumen relativo bajo**: descarta acciones cuyo volumen ha aumentado fuerte durante la corrección (señal de ventas de pánico).
- **Liquidez mínima**: volumen medio diario (en valor) por encima de un mínimo.
- **Sin earnings inminentes**: descarta acciones con resultados dentro de los próximos N días (configurable, o desactivable).
- **Filtro de precio máximo** y **top % por capitalización** por mercado (desactivables).

> El modo `short` existe como opción en la configuración (`short_enabled`) pero todavía no está implementado.

## Estructura del proyecto

```
findStocks/
├── src/findstocks/
│   ├── config.py           # ScreenerConfig: umbrales del screener
│   ├── markets.py          # validación de mercados contra tvscreener
│   ├── screener.py         # obtención de datos + filtrado (lógica pura testeable)
│   ├── output.py           # presentación en consola y export a CSV/XLSX
│   ├── cli.py               # parseo de argumentos, carga del TOML y orquestación
│   └── logging_setup.py
├── tests/                   # tests unitarios (pytest)
├── default.toml             # configuración de ejemplo
├── main.py                  # punto de entrada
└── pyproject.toml
```

## Instalar requisitos

Requiere **Python 3.11+** (se usa `tomllib` de la librería estándar).

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

## Configuración

La configuración ya no se pasa por flags de CLI: vive en un archivo **TOML**. Esto permite tener varios archivos de configuración distintos (por mercado, por estrategia, etc.) y elegir cuál usar en cada ejecución.

`default.toml` de ejemplo:

```toml
[general]
markets = ['FRANCE', 'PORTUGAL', 'BELGIUM', 'NETHERLANDS']
long_enabled = true
short_enabled = false
top_percent = 30        # % top por capitalización a considerar, por mercado
volume_min = 30_000     # volumen medio diario minimo, en valor (cash)
price_max = 160.0
earning_days = 15
stocks_max = 500         # tope de acciones pedidas por mercado antes de filtrar

[long]
rsi_min = 35
rsi_max = 50
adx_min = 15
volume_rel_max = 1.0
performance_min = 0.0
distance_sma200_max = 0.15
```

Los mercados disponibles son los que expone `tvscreener.Market` (`AMERICA`, `FRANCE`, `GERMANY`, `JAPAN`, `CHINA`, `SPAIN`... ver el comentario en `default.toml` para la lista completa). Si se indica un mercado inválido, el script falla con un error explícito.

## Uso

```bash
python3 main.py [opciones]
# o, si instalaste con pip install -e ".[dev]":
findstocks [opciones]
```

Ejemplos:

```bash
# Usa default.toml
python3 main.py

# Usar un archivo de configuración distinto
python3 main.py -c mi_config.toml

# Incluir candidatos aunque tengan earnings próximos (ignora earning_days del TOML)
python3 main.py -e

# Exportar resultados a CSV o Excel
python3 main.py -o candidatos.csv
python3 main.py -o candidatos.xlsx

# Logs detallados
python3 main.py -v
```

### Opciones disponibles

| Opción | Descripción | Valor por defecto |
|---|---|---|
| `-c`, `--config` | Ruta al archivo de configuración TOML. | `default.toml` |
| `-e`, `--show-earnings` | Muestra candidatos aunque tengan earnings próximos (desactiva ese filtro para esta ejecución). | Desactivado |
| `-o`, `--output` | Exporta los resultados a un archivo `.csv` o `.xlsx`. | Sin exportar |
| `-v`, `--verbose` | Muestra logs detallados (nivel debug). | Desactivado |

Todo lo demás (mercados, umbrales de RSI/ADX/volumen, precio máximo, etc.) se define en el archivo TOML indicado con `-c`.

## Salida

El script imprime por consola una tabla con los candidatos encontrados, incluyendo ISIN, nombre, mercado, exchange, precio, capitalización, RSI(14), volumen en valor y volumen relativo. Si ningún valor cumple los criterios ese día, se informa por log.

## Tests

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Los tests cubren la lógica de filtrado (`findstocks.screener.filter_candidates`) y
la validación de mercados (`findstocks.markets`), sin necesidad de red. En cada push
se ejecutan automáticamente vía GitHub Actions (`.github/workflows/ci.yml`), sobre Python 3.11 y 3.12.

## Requisitos

- Python 3.11+
- `pandas`
- `tvscreener`

## Aviso

Esta herramienta es solo para fines informativos/educativos y **no constituye asesoramiento financiero**. Verifica siempre los datos y realiza tu propio análisis antes de tomar decisiones de inversión.
