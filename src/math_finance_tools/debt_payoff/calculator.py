import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from math_finance_tools.debt_payoff.models import (
    AvalancheOutcome,
    CompoundingMode,
    ExtraPaymentComparison,
    HorizonExceededError,
    Loan,
    MonthlySnapshot,
    PayoffResult,
    StrategyVerdict,
)

CENTS = Decimal("0.01")
HORIZON_MONTHS = 120
METHODS = frozenset({"snowball", "avalanche", "avalanche_effective"})


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


def _effective_apr(loan: Loan, year: int, month: int) -> Decimal:
    """The promotional rate through the end of its final month, else the go-to rate."""
    if (
        loan.intro_apr is not None
        and loan.intro_end_date is not None
        and (year, month) <= (loan.intro_end_date.year, loan.intro_end_date.month)
    ):
        return loan.intro_apr
    return loan.apr


def simulate_payoff(
    loans: list[Loan],
    budget: Decimal,
    method: str,
    start_date: date,
    max_months: int = HORIZON_MONTHS,
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

    if method not in METHODS:
        raise ValueError(f"unknown method: {method!r}")

    if method == "snowball":
        priority_order = sorted(loans, key=lambda ln: (ln.balance, ln.name))
    else:
        # "avalanche" sorts once by go-to rate; "avalanche_effective" re-sorts
        # each month below, by the rate in effect that month.
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
            interest = apply_compounding(
                balances[loan.name],
                _effective_apr(loan, current_year, current_month),
                loan.compounding_mode,
                days,
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
        if method == "avalanche_effective":
            priority_order = sorted(
                loans,
                key=lambda ln: (
                    -_effective_apr(ln, current_year, current_month),
                    ln.name,
                ),
            )
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
        raise HorizonExceededError(
            f"simulation did not converge within {max_months} months"
        )

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


_AVALANCHE_ORDERINGS: tuple[tuple[Literal["static", "effective"], str], ...] = (
    ("static", "avalanche"),
    ("effective", "avalanche_effective"),
)


def simulate_best_avalanche(
    loans: list[Loan],
    budget: Decimal,
    start_date: date,
    max_months: int = HORIZON_MONTHS,
) -> AvalancheOutcome:
    """Run both avalanche orderings and return the one that cost less interest.

    An ordering that overruns the horizon is not a candidate. Ties go to static.
    """
    outcomes: list[AvalancheOutcome] = []
    for ordering, method in _AVALANCHE_ORDERINGS:
        try:
            results = simulate_payoff(loans, budget, method, start_date, max_months)
        except HorizonExceededError:
            continue
        outcomes.append(
            AvalancheOutcome(
                results=tuple(results),
                ordering=ordering,
                total_interest=sum((r.total_interest for r in results), Decimal("0")),
            )
        )
    if not outcomes:
        raise HorizonExceededError(
            f"simulation did not converge within {max_months} months"
        )
    # min() keeps the first of equal keys, and static is listed first
    return min(outcomes, key=lambda o: o.total_interest)


def _months_through(start_date: date, month: date) -> int:
    """Whole months from `start_date` through `month`, counting both ends."""
    return (month.year - start_date.year) * 12 + month.month - start_date.month + 1


def compare_strategies(
    loans: list[Loan],
    budget: Decimal,
    start_date: date,
    max_months: int = HORIZON_MONTHS,
) -> StrategyVerdict:
    """Run snowball and the better avalanche ordering and name the cheaper one.

    A tie in total interest goes to snowball: its earlier first clear is then
    the only thing separating them.
    """
    snowball = tuple(simulate_payoff(loans, budget, "snowball", start_date, max_months))
    avalanche = simulate_best_avalanche(loans, budget, start_date, max_months)

    snowball_interest = sum((r.total_interest for r in snowball), Decimal("0"))
    snowball_months = _months_through(start_date, max(r.payoff_date for r in snowball))
    avalanche_months = _months_through(
        start_date, max(r.payoff_date for r in avalanche.results)
    )

    if avalanche.total_interest < snowball_interest:
        winner: Literal["snowball", "avalanche"] = "avalanche"
        winner_interest, loser_interest = avalanche.total_interest, snowball_interest
        months_delta = snowball_months - avalanche_months
    else:
        winner = "snowball"
        winner_interest, loser_interest = snowball_interest, avalanche.total_interest
        months_delta = avalanche_months - snowball_months

    return StrategyVerdict(
        winner=winner,
        winner_total_interest=winner_interest,
        loser_total_interest=loser_interest,
        interest_delta=loser_interest - winner_interest,
        months_delta=months_delta,
        snowball_first_clear_months=_months_through(
            start_date, min(r.payoff_date for r in snowball)
        ),
        avalanche_first_clear_months=_months_through(
            start_date, min(r.payoff_date for r in avalanche.results)
        ),
        avalanche_ordering=avalanche.ordering,
        snowball=snowball,
        avalanche=avalanche,
    )


def minimum_budget_to_clear(
    loans: list[Loan],
    start_date: date,
    max_months: int = HORIZON_MONTHS,
    tolerance: Decimal = Decimal("1"),
) -> Decimal:
    """Smallest monthly budget, to within `tolerance`, that clears every loan
    within `max_months` under snowball and under the better avalanche ordering."""
    if tolerance < CENTS:
        raise ValueError("tolerance must be at least one cent")

    def clears(budget: Decimal) -> bool:
        try:
            simulate_payoff(loans, budget, "snowball", start_date, max_months)
            simulate_best_avalanche(loans, budget, start_date, max_months)
        except HorizonExceededError:
            return False
        return True

    low = sum((ln.min_payment for ln in loans), Decimal("0"))
    if clears(low):
        return low

    # Every balance plus a 31-day month's interest at the higher of its two
    # rates is paid off in full in the first month.
    high = max(
        low,
        sum(
            (
                ln.balance
                + apply_compounding(
                    ln.balance,
                    max(ln.apr, ln.intro_apr or Decimal("0")),
                    ln.compounding_mode,
                    31,
                )
                for ln in loans
            ),
            Decimal("0"),
        ),
    )

    while high - low > tolerance:
        mid = ((low + high) / 2).quantize(CENTS, rounding=ROUND_HALF_UP)
        if clears(mid):
            high = mid
        else:
            low = mid
    return high


def _portfolio_payoff_date(results: list[PayoffResult]) -> date:
    """The month the last loan clears — the whole plan is done then, not before."""
    return max(r.payoff_date for r in results)


def _total_interest(results: list[PayoffResult]) -> Decimal:
    return sum((r.total_interest for r in results), Decimal("0"))


def compare_extra_payment(
    loans: list[Loan],
    budget: Decimal,
    additional_budget: Decimal,
    method: str,
    start_date: date,
    max_months: int = HORIZON_MONTHS,
) -> ExtraPaymentComparison:
    """Run the same loan set twice and diff it: what another monthly amount buys.

    `additional_budget` is the increment between the two runs, not the surplus
    cascaded within one of them. Both runs use `method`, so the comparison
    isolates the money and holds the strategy fixed.
    """
    if additional_budget < 0:
        raise ValueError("additional_budget must not be negative")

    baseline = simulate_payoff(loans, budget, method, start_date, max_months)
    accelerated = simulate_payoff(
        loans, budget + additional_budget, method, start_date, max_months
    )

    baseline_date = _portfolio_payoff_date(baseline)
    accelerated_date = _portfolio_payoff_date(accelerated)
    baseline_interest = _total_interest(baseline)
    accelerated_interest = _total_interest(accelerated)

    return ExtraPaymentComparison(
        baseline=tuple(baseline),
        accelerated=tuple(accelerated),
        baseline_payoff_date=baseline_date,
        accelerated_payoff_date=accelerated_date,
        months_saved=(baseline_date.year - accelerated_date.year) * 12
        + baseline_date.month
        - accelerated_date.month,
        baseline_total_interest=baseline_interest,
        accelerated_total_interest=accelerated_interest,
        interest_saved=(baseline_interest - accelerated_interest).quantize(
            CENTS, rounding=ROUND_HALF_UP
        ),
    )
