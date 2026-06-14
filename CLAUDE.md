# CLAUDE.md

Math and Finance Tools — Streamlit web app with an expanding suite of personal finance calculators.

## Status (2026-06-03)

Phase: initial scaffolding complete. Math logic not yet implemented.
Branch: `first-pass`

## Stack

- Python 3.14+, uv (package manager)
- Streamlit >= 1.36 (multi-page via `st.navigation`, entry point: `Home.py`)
- Plotly >= 5.20 (charts)
- No Pandas
- ruff (lint/format), mypy --strict, pytest 100% coverage target
- hatchling build backend, src layout

## Layout

```
src/math_finance_tools/
    debt_payoff/        # models.py, calculator.py (issue #2)
    composite_rate/     # calculator.py (issue #4)
pages/
    1_Debt_Payoff.py    # issue #3
    2_Composite_Rate.py # issue #5
Home.py                 # landing page (issue #6)
plans/
    math-finance-tools-prd.md   # full PRD with 22 requirements
    math-finance-tools-prd.json # task list JSON
```

## Run

```bash
uv run streamlit run Home.py
uv run pytest --cov=src
ruff format src/ pages/ Home.py && ruff check src/ pages/ Home.py
mypy src/
```

## Key Decisions

- Debt payoff: Snowball (lowest balance first) vs. Avalanche (highest APR first)
- Budget slider: min = sum of minimums (enforced); max = user-configurable input
- Compounding: monthly default, daily toggle; grace period uses calendar end date
- Surplus cascade: excess payment carries to next-priority loan in same month
- Composite rate chart: APR (x), balance (y), scatter; red = above composite, green = below
- No Pandas anywhere; no user accounts or data persistence in v1

## Open Issues

| # | Title |
|---|-------|
| #2 | Implement debt payoff calculator core logic |
| #3 | Build Debt Payoff Calculator Streamlit UI |
| #4 | Implement composite rate calculator logic |
| #5 | Build Composite Rate Calculator Streamlit UI |
| #6 | Write Home.py landing page |
