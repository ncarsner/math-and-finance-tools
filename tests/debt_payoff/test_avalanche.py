from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest

from math_finance_tools.debt_payoff import (
    AvalancheOutcome,
    HorizonExceededError,
    Loan,
    PayoffResult,
    simulate_best_avalanche,
    simulate_payoff,
)

START = date(2026, 1, 1)


def _interest(results: list[PayoffResult]) -> Decimal:
    return sum((r.total_interest for r in results), Decimal("0"))


def _promo_card(intro_end: date) -> Loan:
    return Loan(
        "Card-A",
        Decimal("4000"),
        Decimal("0.29"),
        Decimal("50"),
        intro_apr=Decimal("0.00"),
        intro_end_date=intro_end,
    )


def _expiring_promo() -> list[Loan]:
    # 0% for six months, then 29%
    return [
        _promo_card(date(2026, 6, 1)),
        Loan("Loan-B", Decimal("4000"), Decimal("0.12"), Decimal("50")),
    ]


def _lasting_promo() -> list[Loan]:
    # 0% for four years, longer than the payoff takes
    return [
        _promo_card(date(2030, 1, 1)),
        Loan("Loan-B", Decimal("4000"), Decimal("0.12"), Decimal("50")),
    ]


def _small_promo_beside_high_rate() -> list[Loan]:
    return [
        Loan(
            "Promo-Sm",
            Decimal("1500"),
            Decimal("0.26"),
            Decimal("30"),
            intro_apr=Decimal("0.00"),
            intro_end_date=date(2027, 1, 1),
        ),
        Loan("HighAPR", Decimal("2000"), Decimal("0.24"), Decimal("40")),
        Loan("Big-Low", Decimal("9000"), Decimal("0.07"), Decimal("120")),
    ]


# --- the two orderings, against the measured figures ---


@pytest.mark.parametrize(
    ("loans", "budget", "static", "effective"),
    [
        (_expiring_promo(), Decimal("500"), Decimal("603.15"), Decimal("795.63")),
        (_lasting_promo(), Decimal("500"), Decimal("533.34"), Decimal("210.50")),
        (
            _small_promo_beside_high_rate(),
            Decimal("600"),
            Decimal("1038.53"),
            Decimal("881.84"),
        ),
    ],
    ids=["expiring-promo", "lasting-promo", "small-promo-beside-high-rate"],
)
def test_orderings_reproduce_measured_interest(
    loans: list[Loan], budget: Decimal, static: Decimal, effective: Decimal
) -> None:
    assert _interest(simulate_payoff(loans, budget, "avalanche", START)) == static
    assert (
        _interest(simulate_payoff(loans, budget, "avalanche_effective", START))
        == effective
    )


def test_effective_ordering_resorts_when_the_promo_ends() -> None:
    # During the promo Card-A is at 0%, so surplus goes to Loan-B; once it
    # reverts to 29%, surplus switches to Card-A.
    results = simulate_payoff(
        _expiring_promo(), Decimal("500"), "avalanche_effective", START
    )
    card, loan = results
    assert card.snapshots[0].payment == Decimal("50")
    assert loan.snapshots[0].payment == Decimal("450")
    assert card.snapshots[6].payment > Decimal("50")


# --- simulate_best_avalanche ---


def test_best_avalanche_picks_static_for_an_expiring_promo() -> None:
    outcome = simulate_best_avalanche(_expiring_promo(), Decimal("500"), START)
    assert outcome.ordering == "static"
    assert outcome.total_interest == Decimal("603.15")
    assert outcome.results == tuple(
        simulate_payoff(_expiring_promo(), Decimal("500"), "avalanche", START)
    )


def test_best_avalanche_picks_effective_for_a_lasting_promo() -> None:
    outcome = simulate_best_avalanche(_lasting_promo(), Decimal("500"), START)
    assert outcome.ordering == "effective"
    assert outcome.total_interest == Decimal("210.50")


def test_best_avalanche_tie_resolves_to_static() -> None:
    # No promotional rates: both orderings are the same schedule
    loans = [
        Loan("A", Decimal("3000"), Decimal("0.20"), Decimal("60")),
        Loan("B", Decimal("2000"), Decimal("0.10"), Decimal("40")),
    ]
    outcome = simulate_best_avalanche(loans, Decimal("400"), START)
    assert outcome.ordering == "static"


def test_best_avalanche_skips_an_ordering_that_exceeds_the_horizon() -> None:
    # Static takes 18 months here, effective 17
    outcome = simulate_best_avalanche(
        _lasting_promo(), Decimal("500"), START, max_months=17
    )
    assert outcome.ordering == "effective"


def test_best_avalanche_raises_when_neither_ordering_clears() -> None:
    with pytest.raises(HorizonExceededError, match="within 1 months"):
        simulate_best_avalanche(_lasting_promo(), Decimal("500"), START, max_months=1)


def test_avalanche_outcome_is_frozen() -> None:
    outcome = simulate_best_avalanche(_expiring_promo(), Decimal("500"), START)
    assert isinstance(outcome, AvalancheOutcome)
    with pytest.raises(FrozenInstanceError):
        outcome.ordering = "effective"  # type: ignore[misc]
