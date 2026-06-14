# Changelog

## [Unreleased]

### Added

- Project scaffold: `src/math_finance_tools` package with `debt_payoff` and `composite_rate` subpackages.
- `Home.py` entry point using Streamlit `st.navigation` with sidebar routing.
- Stub pages for Debt Payoff Calculator (`pages/1_Debt_Payoff.py`) and Composite Rate Calculator (`pages/2_Composite_Rate.py`).
- `pyproject.toml` with `streamlit >= 1.36`, `plotly >= 5.20`, hatchling build backend, ruff and mypy config.
- PRD (`plans/math-finance-tools-prd.md`) with 22 requirements and acceptance criteria.
- Task list (`plans/math-finance-tools-prd.json`) with 7 discrete implementation tasks.
- GitHub repository and 7 issues (#1-#7) created from the PRD.
