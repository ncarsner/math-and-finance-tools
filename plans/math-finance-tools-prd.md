# Build a Multi-Tool Math and Finance Web App

## Overview

A Streamlit web app providing an expanding suite of personal finance calculators, starting with a debt payoff strategy comparator and a composite interest rate visualizer. It exists to help users make data-driven decisions about debt repayment by making the math visible and interactive.

## Goals

1. Users can compare snowball vs. avalanche payoff strategies and see the difference in total interest paid and months to payoff within a single session.
2. Users can model real-world loan complexity: variable budgets, minimum payments, promotional/grace-period rates, and daily or monthly compounding.
3. Users can identify which of their accounts drive their blended interest rate above the composite average, informing their own payoff prioritization.
4. The math layer achieves 100% test coverage and is fully decoupled from the UI layer.
5. New tools can be added as new pages without modifying existing ones.

## Non-goals

- No user accounts, login, or persistent data storage (v1).
- No live rate lookups or bank integrations.
- No mobile-native app; responsive Streamlit is acceptable.
- No amortization schedule export (CSV, PDF) in v1.
- No support for variable-rate loans that change on a schedule (beyond the single grace-period intro rate).

## User Stories

- As a borrower with multiple debts, I want to enter my loans and monthly budget so that I can see which payoff method saves me more money.
- As a borrower with a promotional 0% APR card, I want to set a grace period end date and post-promo rate so that the simulation accounts for the rate change automatically.
- As a user adjusting my budget, I want a slider with real-time recalculation so that I can see how an extra $100/month changes my payoff date.
- As a user who is unsure what snowball and avalanche mean, I want familiar labels with descriptive annotations so that I can choose a strategy without reading a finance blog.
- As someone carrying multiple credit card balances, I want to see which accounts are above my composite rate so that I know which ones are most expensive relative to my overall picture.

## Requirements

### Tool 1: Debt Payoff Calculator

1. Users can add and remove individual loan rows, each with: name, balance ($), APR (%), minimum payment ($).
2. Each loan optionally accepts a grace period: intro APR (default 0%), end date, and post-grace APR.
3. A monthly budget slider controls total monthly payment allocation.
4. The app enforces that the monthly budget is greater than or equal to the sum of all minimum payments; if violated, an inline error is shown and calculation is disabled.
5. Users can toggle compounding mode between monthly (APR/12 per period) and daily ((1 + APR/365)^days_in_month per period).
6. The app simulates both snowball (lowest balance first) and avalanche (highest APR first) methods using the same monthly loop.
7. During simulation, when a payment exceeds a loan's remaining balance, the loan is zeroed and the surplus cascades to the next-priority loan in the same month.
8. Grace period rates apply automatically until the specified end date; the standard APR takes effect the following month.
9. Results display a comparison table: method, total interest paid, months to payoff, projected payoff date.
10. Results display a Plotly line chart of total remaining debt over time, one trace per method.
11. Each method's detail is available in an expandable section showing month-by-month per-loan balances.
12. Method labels in the UI read "Snowball (lowest balance first)" and "Avalanche (highest interest first)" with tooltip descriptions explaining the strategy.

### Tool 2: Composite Interest Rate Calculator

13. Users can add and remove account rows, each with: label, balance ($), APR (%).
14. The app calculates and prominently displays the composite weighted average APR: `sum(balance * rate) / sum(balance)`.
15. The app displays the estimated monthly interest cost in dollars: `sum(balance * rate / 12)`.
16. A table shows per-account: label, balance, APR, monthly interest cost, percentage of total interest burden.
17. A Plotly chart plots each account by APR (x-axis) and balance (y-axis or bubble size), with a vertical reference line at the composite rate.
18. Accounts above the composite rate are colored red (high-priority payoff candidates); accounts at or below are colored green.

### Architecture

19. All calculation logic lives in `src/math_finance_tools/`; Streamlit pages import from this package and contain no math.
20. No Pandas dependency; tables use plain Python lists/dicts rendered via `st.dataframe`.
21. Entry point is `Home.py` using Streamlit's `st.navigation` API.
22. Runtime deps limited to `streamlit >= 1.36` and `plotly >= 5.20`; both added to `authorized_libraries.md`.

## Acceptance Criteria

- [ ] R1: Adding/removing loan rows updates inputs immediately; simulation only runs on submit or slider change.
- [ ] R2: Grace period end date picker appears only when grace period toggle is enabled per loan.
- [ ] R3: Budget slider minimum is dynamically set to sum of all minimum payments.
- [ ] R4: Setting budget below minimum sum shows an error message and disables the calculate button.
- [ ] R5: Monthly vs daily toggle changes results for a multi-loan scenario with APR > 0.
- [ ] R6-R8: Snowball and avalanche produce different orderings when loans have unequal balances and rates.
- [ ] R7: Surplus cascade test: with budget set high, zeroing one loan mid-month visibly reduces the next loan's balance in the same period.
- [ ] R8: Loan with grace period ending mid-simulation shows lower total interest than same loan without grace period.
- [ ] R9-R10: Comparison table and line chart render without error for 1, 3, and 10 loans.
- [ ] R11: Expandable detail section shows per-loan monthly data.
- [ ] R12: Hovering or reading method labels shows full strategy description.
- [ ] R13-R18: Composite rate tool: adding two accounts with different rates produces a weighted average between them.
- [ ] R17-R18: Accounts above composite rate are red; accounts below are green; vertical line sits at composite rate.
- [ ] R19: `pytest --cov=src` reports 100% coverage on all files under `src/`.
- [ ] R20: No `import pandas` anywhere in the codebase.
- [ ] R21: `uv run streamlit run Home.py` launches the app with sidebar navigation showing both tools.
- [ ] R22: `pyproject.toml` and `authorized_libraries.md` list streamlit and plotly with version constraints.

## Open Questions

- Should the budget slider have a configurable max, or should it default to 2x or 3x the sum of minimum payments?
- Should grace period end dates be calendar dates (tied to a simulation start date) or N-month counts from today?
- For the composite rate chart, should bubble size represent balance, or should balance be on the y-axis with APR on x? Both encode the same data differently.
- Is there a desired color theme or brand direction for the app, or default Streamlit styling is fine for v1?
- Should `Home.py` display a summary/landing page, or immediately redirect to Tool 1?
