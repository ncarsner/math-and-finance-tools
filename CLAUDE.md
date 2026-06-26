# CLAUDE.md

Math and Finance Tools — Streamlit web app with an expanding suite of personal finance calculators.

## Status (2026-06-26)

Phase: v0 complete. All calculator logic and UI pages implemented and merged to main.
Branch: `main` (SHA 714a212)

## Stack

- Python 3.14+, uv (package manager)
- Streamlit >= 1.36 (multi-page via `st.navigation`, entry point: `Home.py`)
- Plotly >= 5.20 (charts)
- No Pandas
- ruff (lint/format), mypy --strict, pytest 100% branch coverage enforced
- hatchling build backend, src layout

## Layout

```
src/math_finance_tools/
    debt_payoff/
        models.py       # Loan, MonthlySnapshot, PayoffResult, CompoundingMode
        calculator.py   # apply_compounding, simulate_payoff
        __init__.py     # public re-exports
    composite_rate/
        calculator.py   # Account, AccountBreakdown, CompositeRateResult, calculate_composite_rate
        __init__.py     # public re-exports
pages/
    0_Home.py           # landing page (default nav entry)
    1_Debt_Payoff.py    # Debt Payoff Calculator UI
    2_Composite_Rate.py # Composite Rate Calculator UI
tests/
    debt_payoff/
        test_models.py
        test_calculator.py
    composite_rate/
        test_calculator.py
Home.py                 # st.navigation entry point
plans/                  # gitignored — local PRD files only
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
- Compounding: per-loan mode (Monthly default, Daily for student loans); ACT/365 fixed, no leap-year adjustment
- Grace period: compared at (year, month) tuple level; intro APR applies through end of intro_end_date month
- Surplus cascade: excess payment carries to next-priority loan in same month; unspent surplus discarded
- Composite rate chart: APR (x), balance (y), scatter; red = above composite, green = at/below
- Stable ID pattern for dynamic Streamlit rows: each loan/account gets a permanent integer ID; add/remove
  callbacks pre-set or pop session state keys by ID (prevents collisions on mid-list removal)
- Debt Payoff: explicit Calculate button (simulation can be expensive)
- Composite Rate: reactive — recomputes on every render (lightweight)
- No Pandas anywhere; no user accounts or data persistence in v1
- `decimal.Decimal` for all monetary values; `ROUND_HALF_UP` to $0.01 per period

## Open Issues

None — all v0 issues closed (#2, #3, #4, #5, #6, #9, #10, #11).
