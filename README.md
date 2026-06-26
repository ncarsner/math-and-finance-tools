# Math & Finance Tools

A Streamlit web app with a suite of personal finance calculators.

## Calculators

### Debt Payoff Calculator

Compare Snowball (lowest balance first) and Avalanche (highest APR first) debt
payoff strategies side by side. Enter any number of loans with individual APRs,
minimum payments, compounding modes, and optional intro/grace-period APRs. Set a
monthly budget and see a month-by-month payoff schedule, total interest paid, and
a remaining-balance chart for each strategy.

### Composite Rate Calculator

Find the effective blended interest rate across multiple debt accounts. Enter
balances and APRs; the composite rate and monthly interest cost update
immediately. A scatter chart highlights which accounts are above vs. below the
composite rate so you can see where to focus payoff effort first.

## Setup

Requires Python 3.14+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run streamlit run Home.py
```

## Development

```bash
uv run pytest --cov=src            # tests (100% branch coverage required)
ruff format src/ pages/ Home.py    # format
ruff check src/ pages/ Home.py     # lint
mypy src/                          # type-check
```

## Stack

- [Streamlit](https://streamlit.io) >= 1.36 — multi-page UI
- [Plotly](https://plotly.com/python/) >= 5.20 — charts
- [uv](https://github.com/astral-sh/uv) — package management
- [ruff](https://docs.astral.sh/ruff/) — lint and format
- [mypy](https://mypy.readthedocs.io/) `--strict` — type checking
- No pandas
