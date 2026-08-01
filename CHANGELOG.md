# Changelog

## [Unreleased]

### Changed
- La configuración pasa de flags de CLI a un archivo **TOML** (`-c/--config`, por
  defecto `default.toml`), permitiendo mantener varias configuraciones distintas.
- `markets.py` simplificado: ya no expande alias (`EURONEXT` -> lista de países),
  solo valida los mercados contra `tvscreener.Market`.
- `requires-python` corregido a `>=3.11` (el proyecto usa `tomllib`, que no
  existe en versiones anteriores). CI actualizado para testear 3.11 y 3.12
  en vez de 3.10.
- `Price`, `Relative Strength Index (14)` y `Relative Volume` se redondean
  en la salida por consola/export, igual que ya se hacía con capitalización
  y volumen en valor.

### Added
- Opción `short_enabled` en la configuración, reservada para un futuro modo
  short (aún no implementado).

### Fixed
- `tests/test_markets.py` estaba roto (importaba `EURONEXT`/`expand_markets`,
  que ya no existen), lo que rompía `pytest` y por tanto el CI.
- El flag `-e/--show-earnings` se parseaba pero nunca se aplicaba a la
  configuración; ahora desactiva correctamente el filtro de earnings para
  esa ejecución.

### Changed
- Reestructurado el proyecto en un paquete `src/findstocks/` con módulos separados:
  `config`, `markets`, `screener`, `output`, `cli`, `logging_setup`.
- La lógica de filtrado (`filter_candidates`) es ahora una función pura, testeable
  sin necesidad de red ni de la librería `tvscreener`.
- `main.py` pasa a ser un punto de entrada delgado que delega en `findstocks.cli`.

### Added
- Tests unitarios (`pytest`) para `markets` y `screener`.
- Exportación de resultados a CSV/XLSX vía `-o/--output`.
- Flags de CLI adicionales: `--min-adx`, `--max-distance-sma200`, `--min-volume`,
  `--earnings-days`.
- Integración continua con GitHub Actions (lint con `ruff` + tests con `pytest`).
- `pyproject.toml` con entry point `findstocks` instalable vía `pip install -e .`.
- `.gitignore`.

### Fixed
- Corregido el texto de ayuda de `--top`, que indicaba un valor por defecto (20)
  distinto del real (30).
