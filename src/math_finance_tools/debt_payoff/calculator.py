import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from math_finance_tools.debt_payoff.models import (
    CompoundingMode,
    Loan,
    MonthlySnapshot,
    PayoffResult,
)

CENTS = Decimal("0.01")


def apply_compounding(
    principal: Decimal,
    apr: Decimal,
    mode: CompoundingMode,
    days_in_month: int,
) -> Decimal:
    if mode == CompoundingMode.MONTHLY:
        return (principal * apr / 12).quantize(CENTS, rounding=ROUND_HALF_UP)
    return (principal * ((1 + apr / 365) ** days_in_month - 1)).quantize(
        CENTS, rounding=ROUND_HALF_UP
    )


def simulate_payoff(
    loans: list[Loan],
    budget: Decimal,
    method: str,
    start_date: date,
    max_months: int = 1200,
) -> list[PayoffResult]:
    if not loans:
        raise ValueError("loans list must not be empty")

    for loan in loans:
        if loan.balance <= 0:
            raise ValueError(f"loan balance must be positive: {loan.name!r}")

    names = [loan.name for loan in loans]
    if len(names) != len(set(names)):
        raise ValueError("duplicate loan names")

    if budget < sum(loan.min_payment for loan in loans):
        raise ValueError("budget must be >= sum of minimum payments")

    if method not in {"snowball", "avalanche"}:
        raise ValueError(f"unknown method: {method!r}")

    if method == "snowball":
        priority_order = sorted(loans, key=lambda ln: (ln.balance, ln.name))
    else:
        priority_order = sorted(loans, key=lambda ln: (-ln.apr, ln.name))

    balances: dict[str, Decimal] = {ln.name: ln.balance for ln in loans}
    per_loan_snapshots: dict[str, list[MonthlySnapshot]] = {ln.name: [] for ln in loans}

    current_year = start_date.year
    current_month = start_date.month
    months_elapsed = 0

    while any(balances[ln.name] > 0 for ln in loans) and months_elapsed < max_months:
        month_date = date(current_year, current_month, 1)
        days = calendar.monthrange(current_year, current_month)[1]

        active_loans = [ln for ln in loans if balances[ln.name] > 0]

        # Accrue interest
        interest_charged: dict[str, Decimal] = {}
        for loan in active_loans:
            if (
                loan.intro_apr is not None
                and loan.intro_end_date is not None
                and (current_year, current_month)
                <= (loan.intro_end_date.year, loan.intro_end_date.month)
            ):
                effective_apr = loan.intro_apr
            else:
                effective_apr = loan.apr
            interest = apply_compounding(
                balances[loan.name], effective_apr, loan.compounding_mode, days
            )
            balances[loan.name] += interest
            interest_charged[loan.name] = interest

        # Pay minimums
        pool = budget
        min_paid: dict[str, Decimal] = {}
        for loan in active_loans:
            capped = min(loan.min_payment, balances[loan.name])
            balances[loan.name] -= capped
            pool -= capped
            min_paid[loan.name] = capped

        # Distribute surplus in priority order
        extra_paid: dict[str, Decimal] = {}
        for loan in priority_order:
            if pool <= 0:
                break
            if balances[loan.name] <= 0:
                continue
            extra = min(pool, balances[loan.name])
            balances[loan.name] -= extra
            pool -= extra
            extra_paid[loan.name] = extra

        # Build snapshots
        for loan in active_loans:
            total_payment = min_paid[loan.name] + extra_paid.get(
                loan.name, Decimal("0")
            )
            interest = interest_charged[loan.name]
            snap = MonthlySnapshot(
                loan_name=loan.name,
                month=month_date,
                payment=total_payment,
                interest=interest,
                principal=total_payment - interest,
                remaining_balance=max(balances[loan.name], Decimal("0")),
            )
            per_loan_snapshots[loan.name].append(snap)

        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
        months_elapsed += 1

    if months_elapsed >= max_months and any(balances[ln.name] > 0 for ln in loans):
        raise ValueError(f"simulation did not converge within {max_months} months")

    return [
        PayoffResult(
            loan_name=loan.name,
            snapshots=tuple(per_loan_snapshots[loan.name]),
            total_interest=sum(
                (s.interest for s in per_loan_snapshots[loan.name]), Decimal("0")
            ),
            payoff_date=(
                per_loan_snapshots[loan.name][-1].month
                if per_loan_snapshots[loan.name]
                else start_date
            ),
        )
        for loan in loans
    ]
