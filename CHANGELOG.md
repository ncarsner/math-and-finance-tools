# Changelog

## [Unreleased]

## [0.1.0] - 2026-06-26

### Added

- Debt Payoff Calculator UI (`pages/1_Debt_Payoff.py`): dynamic loan rows with
  stable session-state IDs, per-loan compounding mode (Monthly/Daily), optional
  grace-period APR toggle, budget ceiling input with slider (min locked to sum of
  minimum payments), Snowball vs. Avalanche comparison table, Plotly debt-over-time
  line chart, per-method monthly detail expanders.
- Composite Rate Calculator UI (`pages/2_Composite_Rate.py`): reactive composite
  rate computation, `st.metric` for composite APR and monthly interest cost,
  per-account breakdown table, Plotly APR-vs-balance scatter with red/green
  coloring and dashed composite-rate reference line.
- Home landing page (`pages/0_Home.py`) as default navigation entry describing
  both calculators.
- Debt payoff core logic (`src/math_finance_tools/debt_payoff/`): `Loan`,
  `MonthlySnapshot`, `PayoffResult`, `CompoundingMode` models; `apply_compounding`
  and `simulate_payoff` with Snowball/Avalanche sorting, surplus cascade, grace
  period support, and per-loan compounding mode.
- Composite rate core logic (`src/math_finance_tools/composite_rate/`): `Account`,
  `AccountBreakdown`, `CompositeRateResult`, `calculate_composite_rate`.
- pytest configuration with 100% branch coverage enforcement; full test suite
  covering both calculators.
- Project scaffold: `src/math_finance_tools` package, `Home.py` entry point,
  stub pages, `pyproject.toml` with ruff, mypy, and hatchling config.
