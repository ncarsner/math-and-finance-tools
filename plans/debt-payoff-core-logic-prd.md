# Implement Debt Payoff Calculator Core Logic

## Overview

Pure-math simulation layer for debt payoff strategy comparison (snowball vs. avalanche), with per-loan compounding mode, grace period rate switching, and surplus cascade. It exists to provide empirically accurate, fully-tested calculation logic that the Streamlit UI (issue #3) can import without containing any math.

## Goals

1. `pytest --cov=src` reports 100% branch coverage on `debt_payoff/calculator.py` and `debt_payoff/models.py`.
2. Single-loan payoff month and total interest match a hand calculation for a given APR and budget.
3. Snowball and avalanche produce different payoff orderings when loans have unequal balances and unequal rates.
4. Daily and monthly compounding produce measurably different total interest for the same loan over a 90+ month horizon.
5. All edge cases — surplus cascade, grace period boundary, budget equal to sum of minimums — terminate correctly and without error.

## Non-goals

- No Streamlit or UI code (issue #3 covers that).
- No Pandas anywhere in the implementation or tests.
- No data persistence or user accounts.
- No composite rate logic (issue #4).
- No variable-rate loans beyond a single intro/grace-period rate per loan.
- No amortization schedule export.

## User Stories

- As the simulation engine, I want empirically accurate interest calculations per loan per month so that total interest projections match real-world lender statements.
- As a developer writing tests, I want all types to be immutable so that I can assert on results without worrying about mutation side effects.
- As the Streamlit UI layer (issue #3), I want a clean public import surface (`from math_finance_tools.debt_payoff import Loan, simulate_payoff`) so that the page contains no math logic.
- As a user with a student loan, I want daily compounding calculated correctly so that the simulation reflects how my lender actually accrues interest.
- As a user with a 0% intro APR card, I want the grace period to switch automatically at the right month so that my total interest reflects the promotional rate.

## Requirements

### Data Models (`models.py`)

1. `CompoundingMode` enum with values `MONTHLY` and `DAILY`.
2. `Loan` frozen dataclass with fields: `name: str`, `balance: Decimal`, `apr: Decimal` (post-grace, as fraction e.g. `Decimal("0.1999")`), `min_payment: Decimal`, `compounding_mode: CompoundingMode = CompoundingMode.MONTHLY`, `intro_apr: Decimal | None = None`, `intro_end_date: date | None = None`.
3. `MonthlySnapshot` frozen dataclass with fields: `loan_name: str`, `month: date` (normalized to first of month), `payment: Decimal`, `interest: Decimal`, `principal: Decimal`, `remaining_balance: Decimal`.
4. `PayoffResult` frozen dataclass with fields: `loan_name: str`, `snapshots: tuple[MonthlySnapshot, ...]`, `total_interest: Decimal`, `payoff_date: date`.

### Calculator (`calculator.py`)

5. `apply_compounding(principal, apr, mode, days_in_month) -> Decimal`: monthly returns `(principal * apr / 12).quantize(CENTS, ROUND_HALF_UP)`; daily returns `(principal * ((1 + apr / 365) ** days_in_month - 1)).quantize(CENTS, ROUND_HALF_UP)`. Daily rate divisor is fixed at 365 regardless of leap year.
6. `simulate_payoff(loans, budget, method, start_date, max_months=1200) -> list[PayoffResult]`: validates inputs, sorts loans by method, runs monthly loop, returns one `PayoffResult` per loan in original input order.
7. Monthly loop: for each month, accrue interest on all active loans using each loan's own `compounding_mode`; pay minimums across all active loans (capped to remaining balance); distribute surplus to priority-sorted active loans in order.
8. Surplus cascade: when a payment exceeds a loan's remaining balance, the loan is zeroed and the remainder carries to the next-priority loan in the same month. Unspent surplus after all loans are zeroed is discarded.
9. Grace period: use `intro_apr` while `(current_year, current_month) <= (intro_end_date.year, intro_end_date.month)`; switch to `apr` the following month. Grace period applies only when both `intro_apr` and `intro_end_date` are non-None.
10. Month arithmetic uses integer carry-over (`current_month += 1; if > 12: reset to 1, increment year`); no `timedelta` for month advancement.
11. Input validation raises `ValueError` for: empty `loans` list; any loan with `balance <= 0`; duplicate `loan.name` values; `budget < sum(l.min_payment for l in loans)`; `method` not in `{"snowball", "avalanche"}`; simulation not converging within `max_months`.

### Package Interface (`__init__.py`)

12. `debt_payoff/__init__.py` re-exports `CompoundingMode`, `Loan`, `MonthlySnapshot`, `PayoffResult`, `apply_compounding`, `simulate_payoff` using the `X as X` explicit re-export pattern for mypy `no_implicit_reexport` compatibility.

### Testing & Tooling

13. `pyproject.toml` adds `pytest>=8` and `pytest-cov>=6` to `[dependency-groups] dev`; adds `[tool.pytest.ini_options]` with `--cov=src --cov-fail-under=100`; adds `[tool.coverage.run]` with `branch = true`.
14. `tests/` and `tests/debt_payoff/` directories created with empty `__init__.py` files.
15. `tests/debt_payoff/test_models.py` covers: `CompoundingMode` values, all `Loan` fields including defaults, `MonthlySnapshot` fields, `PayoffResult` fields, frozen enforcement on both frozen types.
16. `tests/debt_payoff/test_calculator.py` covers all seven AC scenarios plus all `ValueError` branches and `apply_compounding` unit tests.

## Acceptance Criteria

- [ ] R1–R4: All four types import cleanly; `mypy src/` passes with `--strict`; frozen types raise `FrozenInstanceError` on field assignment.
- [ ] R5: `apply_compounding` monthly and daily return different values for the same principal, APR, and 30-day month; daily returns more than monthly for a 31-day month.
- [ ] R6–R10: `simulate_payoff` with a single known loan returns a payoff date and total interest matching hand calculation.
- [ ] R7: Snowball and avalanche return different first-payoff loan for a two-loan scenario where the lower-balance loan has a lower APR (e.g. balance=300 APR=5% vs balance=500 APR=20%).
- [ ] R8: Surplus cascade: high budget in month 1 zeros a small loan; the larger loan's month-1 snapshot shows a payment exceeding its minimum.
- [ ] R9: Grace period loan's `total_interest` is less than an otherwise-identical loan without a grace period.
- [ ] R10: `budget == sum(min_payments)` run terminates without error when each minimum exceeds monthly interest.
- [ ] R11: All six `ValueError` paths each have a dedicated test; each raises on the correct condition.
- [ ] R12: `pytest --cov=src --cov-fail-under=100` passes with `branch = true`.
- [ ] R13: `ruff check src/ tests/` and `ruff format --check src/ tests/` both exit 0.
- [ ] R14–R16: Test infrastructure created; `uv run pytest` discovers and runs all tests without configuration errors.

## Open Questions

None — all design decisions resolved in grill-me session (2026-06-26):

| Decision | Resolution |
|----------|------------|
| Daily rate divisor | Fixed 365 (ACT/365 fixed convention) |
| Grace period boundary | Month-level `(year, month)` tuple comparison |
| `PayoffResult.snapshots` type | `tuple[MonthlySnapshot, ...]` |
| Unspent surplus | Silently discarded |
| AC4 loan duration | ~93-month loan to surface annual EAR difference |
| Compounding mode scope | Per-loan field on `Loan`; default `MONTHLY` |
| `Loan` mutability | `frozen=True` |
| Rounding | Inside `apply_compounding`, `ROUND_HALF_UP` to `$0.01` |
| Duplicate loan names | `ValueError` in `simulate_payoff` |
| Zero-balance loans | `ValueError` in `simulate_payoff` |
