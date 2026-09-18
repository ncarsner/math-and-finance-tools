import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from math_finance_tools.debt_payoff import (
    ExtraPaymentComparison,
    HorizonExceededError,
    Loan,
    compare_extra_payment,
)

START = date(2026, 1, 1)


def _loans() -> list[Loan]:
    return [
        Loan("Card", Decimal("6000"), Decimal("0.22"), Decimal("120")),
        Loan("Auto", Decimal("9000"), Decimal("0.06"), Decimal("180")),
    ]


# --- R6: no additional budget is no difference ---


def test_zero_additional_budget_saves_nothing() -> None:
    result = compare_extra_payment(
        _loans(), Decimal("400"), Decimal("0"), "snowball", START
    )
    assert result.months_saved == 0
    assert result.interest_saved == Decimal("0.00")
    assert result.baseline_payoff_date == result.accelerated_payoff_date
    assert result.baseline_total_interest == result.accelerated_total_interest


# --- R7: a positive additional budget never costs months or interest ---


def test_positive_additional_budget_clears_sooner_for_less() -> None:
    result = compare_extra_payment(
        _loans(), Decimal("400"), Decimal("250"), "snowball", START
    )
    assert result.accelerated_payoff_date < result.baseline_payoff_date
    assert result.months_saved > 0
    assert result.interest_saved > 0
    assert result.accelerated_total_interest < result.baseline_total_interest


def test_both_runs_cover_every_loan() -> None:
    result = compare_extra_payment(
        _loans(), Decimal("400"), Decimal("100"), "avalanche", START
    )
    assert [r.loan_name for r in result.baseline] == ["Card", "Auto"]
    assert [r.loan_name for r in result.accelerated] == ["Card", "Auto"]


def test_holds_the_strategy_fixed_across_both_runs() -> None:
    # The lower balance carries the lower rate, so the two strategies disagree.
    # Each comparison keeps its own ordering in both of its runs: it isolates
    # the money, not the strategy.
    split = [
        Loan("Small-Low", Decimal("1000"), Decimal("0.05"), Decimal("25")),
        Loan("Big-High", Decimal("5000"), Decimal("0.20"), Decimal("100")),
    ]
    snowball = compare_extra_payment(
        split, Decimal("400"), Decimal("100"), "snowball", START
    )
    avalanche = compare_extra_payment(
        split, Decimal("400"), Decimal("100"), "avalanche", START
    )
    for run in (snowball.baseline, snowball.accelerated):
        by_name = {r.loan_name: r for r in run}
        assert by_name["Small-Low"].payoff_date < by_name["Big-High"].payoff_date
    for run in (avalanche.baseline, avalanche.accelerated):
        by_name = {r.loan_name: r for r in run}
        assert by_name["Big-High"].payoff_date < by_name["Small-Low"].payoff_date
    assert avalanche.baseline_total_interest < snowball.baseline_total_interest


# --- R8: portfolio payoff date and month arithmetic ---


def test_payoff_date_is_the_last_loan_to_clear() -> None:
    result = compare_extra_payment(
        _loans(), Decimal("400"), Decimal("0"), "snowball", START
    )
    assert result.baseline_payoff_date == max(r.payoff_date for r in result.baseline)
    assert result.baseline_payoff_date > min(r.payoff_date for r in result.baseline)


def test_months_saved_spans_the_year_boundary() -> None:
    # Baseline Feb 2028 against accelerated Nov 2027 is three months, not nine.
    quick = Loan("Quick", Decimal("2600"), Decimal("0.00"), Decimal("100"))
    result = compare_extra_payment(
        [quick], Decimal("100"), Decimal("15"), "snowball", START
    )
    assert result.baseline_payoff_date == date(2028, 2, 1)
    assert result.accelerated_payoff_date == date(2027, 11, 1)
    assert result.months_saved == 3


# --- R8: interest_saved is quantized money ---


def test_interest_saved_is_quantized_to_cents() -> None:
    result = compare_extra_payment(
        _loans(), Decimal("400"), Decimal("75"), "snowball", START
    )
    assert result.interest_saved == result.interest_saved.quantize(Decimal("0.01"))
    assert result.interest_saved == (
        result.baseline_total_interest - result.accelerated_total_interest
    )


# --- R9: validation ---


def test_negative_additional_budget_raises() -> None:
    with pytest.raises(ValueError, match="additional_budget"):
        compare_extra_payment(
            _loans(), Decimal("400"), Decimal("-1"), "snowball", START
        )


def test_negative_additional_budget_is_rejected_before_simulating() -> None:
    # Loans that would themselves raise; the additional_budget check comes first.
    with pytest.raises(ValueError, match="additional_budget"):
        compare_extra_payment([], Decimal("400"), Decimal("-1"), "snowball", START)


def test_budget_below_minimums_propagates_unchanged() -> None:
    with pytest.raises(ValueError, match="sum of minimum payments"):
        compare_extra_payment(
            _loans(), Decimal("200"), Decimal("50"), "snowball", START
        )


def test_unknown_method_propagates_unchanged() -> None:
    with pytest.raises(ValueError, match="unknown method"):
        compare_extra_payment(
            _loans(), Decimal("400"), Decimal("50"), "optimistic", START
        )


def test_baseline_overrunning_the_horizon_propagates() -> None:
    stuck = Loan("Stuck", Decimal("12000"), Decimal("0.26"), Decimal("260"))
    with pytest.raises(HorizonExceededError):
        compare_extra_payment(
            [stuck], Decimal("260"), Decimal("500"), "snowball", START, max_months=6
        )


# --- Frozen ---


def test_comparison_is_frozen() -> None:
    result = compare_extra_payment(
        _loans(), Decimal("400"), Decimal("0"), "snowball", START
    )
    assert isinstance(result, ExtraPaymentComparison)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.months_saved = 99  # type: ignore[misc]
