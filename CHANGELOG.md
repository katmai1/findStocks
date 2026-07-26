# Changelog

## [Unreleased]

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
