# Math & Finance Tools

A Streamlit web app with a suite of personal finance calculators. The design
center is self-driven debt resolution over a two-to-seven-year horizon: what to
pay first, what it costs, and what paying more would buy.

## Calculators

### Debt Payoff Calculator

Compare **Snowball** (lowest balance first) against **Avalanche** (rate-driven)
side by side. Enter any number of loans with individual APRs, minimum payments,
compounding modes (monthly or daily) and optional intro/grace-period APRs, set a
monthly budget, and the page reports:

- **A verdict naming the winner** at every margin, with the interest it saves and
  the months it adds or removes. A small win is reported as small, never as a tie.
- **Total interest, payoff date, and the month the first loan clears** for each
  strategy — the tradeoff snowball is usually chosen for.
- **What an additional monthly amount would buy**, as months and interest saved
  against the same strategy at the lower budget. At zero it does not run.
- **A remaining-balance chart** for both strategies, and for both again at the
  higher budget when an additional amount is set.
- **A month-by-month schedule** per strategy.

Avalanche is computed as the better of two orderings — one by the go-to rate, one
by the rate actually in effect each month — because neither wins universally once
promotional rates are in play. The page labels whichever it used.

Anything not cleared within ten years is reported as *impossible at this budget*,
along with the monthly budget that would clear it.

#### Worked examples

A loan set whose balance order matches its rate order makes both strategies pay
the same loans in the same sequence, so the results agree to the cent and the
chart traces overlap exactly. **Load a worked example** at the top of the page
fills the whole form with a set built to show a real disagreement:

| Example | What it shows |
|---|---|
| Avalanche saves the most | A large high-rate card behind two small cheap debts |
| Snowball buys an early win | An early clear that costs very little interest |
| Promotional rates in play | Intro rates expiring at different times |
| Student loan, daily compounding | Daily compounding against a cheap loan and an expensive card |
| Budget too tight to clear | A budget that cannot clear the debt inside ten years |

### Composite Rate Calculator

Find the effective blended interest rate across multiple debt accounts. Enter
balances and APRs; the composite rate and monthly interest cost update
immediately. A scatter chart marks which accounts sit above the composite rate —
the highest-priority payoff targets — and which are at or below it.

The computed rate carries over to Debt vs. Invest as a starting debt rate.

### Debt vs. Invest

Decide whether a spare dollar is worth more against the debt or in the market.
The debt rate is compared against an expected return **after tax** — taken whole
in a tax-advantaged account, reduced by capital gains tax in a taxable brokerage —
and the page names the side the spread favors, or reports indifference when the
two are exactly equal.

Both sides are nominal, so inflation cancels between them. Contribution
schedules, employer match and market paths are not modeled.

## Setup

Requires Python 3.14+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run streamlit run Home.py
```

## Development

```bash
uv run pytest --cov=src                  # tests (100% branch coverage required)
ruff format src/ views/ tests/ Home.py   # format
ruff check src/ views/ tests/ Home.py    # lint
uv run mypy src/                         # type-check
```

Calculation logic lives in `src/math_finance_tools/`, one package per calculator,
and is covered to 100% branches. The Streamlit pages live in `views/` and are
exercised through `streamlit.testing.v1.AppTest`.

## Stack

- [Streamlit](https://streamlit.io) >= 1.36 — multi-page UI via `st.navigation`
- [Plotly](https://plotly.com/python/) >= 5.20 — charts
- [uv](https://github.com/astral-sh/uv) — package management
- [ruff](https://docs.astral.sh/ruff/) — lint and format
- [mypy](https://mypy.readthedocs.io/) `--strict` — type checking
- `decimal.Decimal` for all monetary values
- No pandas
