from datetime import date
from decimal import Decimal

import pytest

from math_finance_tools.debt_payoff import (
    CompoundingMode,
    HorizonExceededError,
    Loan,
    minimum_budget_to_clear,
    simulate_payoff,
)

START = date(2025, 1, 1)


def _clears(loans: list[Loan], budget: Decimal) -> bool:
    try:
        for method in ("snowball", "avalanche"):
            simulate_payoff(loans, budget, method, START)
    except HorizonExceededError:
        return False
    return True


# --- simulate_payoff horizon ---


def test_default_horizon_is_120_months() -> None:
    # 18% on $5000 at $80/month needs 187 months
    loan = Loan("A", Decimal("5000"), Decimal("0.18"), Decimal("80"))
    with pytest.raises(HorizonExceededError, match="within 120 months"):
        simulate_payoff([loan], Decimal("80"), "snowball", START)


def test_horizon_exceeded_is_still_a_value_error() -> None:
    loan = Loan("A", Decimal("10000"), Decimal("0.24"), Decimal("10"))
    with pytest.raises(ValueError, match="did not converge"):
        simulate_payoff([loan], Decimal("10"), "snowball", START)


def test_ordinary_consolidation_clears_near_the_cap() -> None:
    # $20k at 8% daily against $250/month: 115 months, inside the horizon
    loan = Loan(
        "Consolidation",
        Decimal("20000"),
        Decimal("0.08"),
        Decimal("250"),
        compounding_mode=CompoundingMode.DAILY,
    )
    results = simulate_payoff([loan], Decimal("250"), "snowball", START)
    assert len(results[0].snapshots) == 115


def test_validation_errors_are_not_horizon_errors() -> None:
    loan = Loan("A", Decimal("500"), Decimal("0.12"), Decimal("25"))
    with pytest.raises(ValueError) as info:
        simulate_payoff([loan, loan], Decimal("100"), "snowball", START)
    assert not isinstance(info.value, HorizonExceededError)


# --- minimum_budget_to_clear ---


def test_minimum_budget_is_tight() -> None:
    loans = [
        Loan("Card", Decimal("8000"), Decimal("0.24"), Decimal("160")),
        Loan("Auto", Decimal("12000"), Decimal("0.07"), Decimal("150")),
    ]
    tolerance = Decimal("1")
    budget = minimum_budget_to_clear(loans, START, tolerance=tolerance)

    assert budget > sum(ln.min_payment for ln in loans), "fixture must bisect"
    assert _clears(loans, budget)
    assert not _clears(loans, budget - tolerance - Decimal("1"))


def test_minimum_budget_is_sum_of_minimums_when_that_clears() -> None:
    # lower bound: the minimums alone already clear
    loans = [Loan("A", Decimal("500"), Decimal("0.12"), Decimal("50"))]
    assert minimum_budget_to_clear(loans, START) == Decimal("50")


def test_minimum_budget_upper_bound_clears_in_one_month() -> None:
    # upper bound: nothing short of the whole balance clears in a 1-month horizon
    loans = [
        Loan(
            "Promo",
            Decimal("3000"),
            Decimal("0.29"),
            Decimal("30"),
            compounding_mode=CompoundingMode.DAILY,
            intro_apr=Decimal("0.00"),
            intro_end_date=date(2025, 6, 30),
        ),
        Loan("Card", Decimal("1000"), Decimal("0.18"), Decimal("25")),
    ]
    budget = minimum_budget_to_clear(loans, START, max_months=1)
    total = sum(
        (
            r.snapshots[0].payment
            for r in simulate_payoff(loans, budget, "avalanche", START, max_months=1)
        ),
        Decimal("0"),
    )
    assert budget >= total
    assert budget - total <= Decimal("1")


def test_minimum_budget_upper_bound_respects_large_minimums() -> None:
    # a minimum larger than the balance keeps the bound at or above the minimums
    loans = [Loan("Tiny", Decimal("40"), Decimal("0.10"), Decimal("100"))]
    assert minimum_budget_to_clear(loans, START, max_months=1) == Decimal("100")


def test_minimum_budget_rejects_sub_cent_tolerance() -> None:
    loans = [Loan("A", Decimal("500"), Decimal("0.12"), Decimal("50"))]
    with pytest.raises(ValueError, match="tolerance"):
        minimum_budget_to_clear(loans, START, tolerance=Decimal("0.001"))


def test_minimum_budget_propagates_invalid_loans() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        minimum_budget_to_clear([], START)
