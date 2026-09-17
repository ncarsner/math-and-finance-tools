from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest

from math_finance_tools.debt_payoff import (
    HorizonExceededError,
    Loan,
    StrategyVerdict,
    compare_strategies,
    simulate_best_avalanche,
    simulate_payoff,
)

START = date(2026, 1, 1)


def _small_low_beside_big_high() -> list[Loan]:
    # The lower-balance loan carries the lower rate: the strategies disagree
    return [
        Loan("Small-Low", Decimal("1000"), Decimal("0.05"), Decimal("25")),
        Loan("Big-High", Decimal("5000"), Decimal("0.20"), Decimal("100")),
    ]


def test_avalanche_wins_when_the_small_loan_is_the_cheap_one() -> None:
    verdict = compare_strategies(_small_low_beside_big_high(), Decimal("400"), START)

    assert verdict.winner == "avalanche"
    assert verdict.winner_total_interest == Decimal("759.60")
    assert verdict.loser_total_interest == Decimal("926.31")
    assert verdict.interest_delta == Decimal("166.71")
    assert verdict.avalanche_ordering == "static"


def test_snowball_clears_its_first_loan_sooner() -> None:
    verdict = compare_strategies(_small_low_beside_big_high(), Decimal("400"), START)

    # Snowball clears Small-Low in Apr 2026; avalanche clears Big-High in Apr 2027
    assert verdict.snowball_first_clear_months == 4
    assert verdict.avalanche_first_clear_months == 16
    assert verdict.snowball_first_clear_months < verdict.avalanche_first_clear_months


def test_months_delta_is_loser_duration_minus_winner_duration() -> None:
    # Snowball runs through Jun 2027 (18 months), avalanche through May 2027 (17)
    verdict = compare_strategies(_small_low_beside_big_high(), Decimal("400"), START)
    assert verdict.months_delta == 1


def test_months_are_counted_inclusively() -> None:
    # Cleared within the start month counts as one month, not zero
    loans = [Loan("A", Decimal("100"), Decimal("0.10"), Decimal("25"))]
    verdict = compare_strategies(loans, Decimal("500"), START)
    assert verdict.snowball_first_clear_months == 1
    assert verdict.avalanche_first_clear_months == 1


def test_tie_resolves_to_snowball() -> None:
    loans = [Loan("Only", Decimal("3000"), Decimal("0.18"), Decimal("100"))]
    verdict = compare_strategies(loans, Decimal("300"), START)

    assert verdict.winner == "snowball"
    assert verdict.interest_delta == Decimal("0")
    assert verdict.months_delta == 0


def test_verdict_carries_the_runs_it_was_computed_from() -> None:
    loans = _small_low_beside_big_high()
    verdict = compare_strategies(loans, Decimal("400"), START)

    assert verdict.snowball == tuple(
        simulate_payoff(loans, Decimal("400"), "snowball", START)
    )
    assert verdict.avalanche == simulate_best_avalanche(loans, Decimal("400"), START)


def test_horizon_error_propagates() -> None:
    loans = [Loan("A", Decimal("5000"), Decimal("0.30"), Decimal("100"))]
    with pytest.raises(HorizonExceededError):
        compare_strategies(loans, Decimal("100"), START)


def test_strategy_verdict_is_frozen() -> None:
    verdict = compare_strategies(_small_low_beside_big_high(), Decimal("400"), START)
    assert isinstance(verdict, StrategyVerdict)
    with pytest.raises(FrozenInstanceError):
        verdict.winner = "snowball"  # type: ignore[misc]
