from decimal import Decimal

from math_finance_tools.composite_rate.calculator import (
    Account,
    calculate_composite_rate,
)


def test_two_equal_balance_composite_is_average() -> None:
    accounts = [
        Account("Card A", Decimal("1000"), Decimal("0.10")),
        Account("Card B", Decimal("1000"), Decimal("0.20")),
    ]
    result = calculate_composite_rate(accounts)
    assert result.composite_apr == Decimal("0.150000")


def test_one_zero_apr_weighted_toward_nonzero() -> None:
    accounts = [
        Account("No Interest", Decimal("500"), Decimal("0.00")),
        Account("High Rate", Decimal("500"), Decimal("0.20")),
    ]
    result = calculate_composite_rate(accounts)
    assert Decimal("0") < result.composite_apr < Decimal("0.20")
    assert result.composite_apr == Decimal("0.100000")


def test_all_same_rate_composite_equals_that_rate() -> None:
    accounts = [
        Account("A", Decimal("200"), Decimal("0.15")),
        Account("B", Decimal("800"), Decimal("0.15")),
        Account("C", Decimal("500"), Decimal("0.15")),
    ]
    result = calculate_composite_rate(accounts)
    assert result.composite_apr == Decimal("0.150000")


def test_zero_total_balance_returns_zero() -> None:
    accounts = [
        Account("Paid Off", Decimal("0"), Decimal("0.18")),
    ]
    result = calculate_composite_rate(accounts)
    assert result.composite_apr == Decimal("0")
    assert result.monthly_interest_cost == Decimal("0")
    assert result.per_account_breakdown[0].interest_share == Decimal("0")


def test_monthly_interest_cost_correct() -> None:
    accounts = [
        Account("Card", Decimal("1200"), Decimal("0.12")),
    ]
    result = calculate_composite_rate(accounts)
    assert result.monthly_interest_cost == Decimal("12.00")


def test_per_account_breakdown_fields() -> None:
    accounts = [
        Account("A", Decimal("600"), Decimal("0.12")),
        Account("B", Decimal("400"), Decimal("0.18")),
    ]
    result = calculate_composite_rate(accounts)
    by_label = {b.label: b for b in result.per_account_breakdown}
    assert by_label["A"].monthly_interest == Decimal("6.00")
    assert by_label["B"].monthly_interest == Decimal("6.00")
    assert by_label["A"].interest_share == Decimal("0.500000")
    assert by_label["B"].interest_share == Decimal("0.500000")


def test_composite_weighted_toward_higher_balance() -> None:
    accounts = [
        Account("Low", Decimal("100"), Decimal("0.05")),
        Account("High", Decimal("900"), Decimal("0.20")),
    ]
    result = calculate_composite_rate(accounts)
    # composite = (100*0.05 + 900*0.20) / 1000 = 185/1000 = 0.185
    assert result.composite_apr == Decimal("0.185000")


def test_zero_total_monthly_interest_share_zero() -> None:
    # All accounts at 0% → monthly_interest=0, interest_share should not divide by zero
    accounts = [
        Account("A", Decimal("1000"), Decimal("0.00")),
        Account("B", Decimal("500"), Decimal("0.00")),
    ]
    result = calculate_composite_rate(accounts)
    assert result.monthly_interest_cost == Decimal("0")
    for bd in result.per_account_breakdown:
        assert bd.interest_share == Decimal("0")
