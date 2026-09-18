import dataclasses
from decimal import Decimal

import pytest

from math_finance_tools.debt_vs_invest import (
    AccountType,
    DebtVsInvestResult,
    Recommendation,
    compare_debt_vs_invest,
)

CGR = Decimal("0.15")


# --- R14, R15, R16: the three recommendations ---


def test_expensive_debt_beats_a_market_return() -> None:
    result = compare_debt_vs_invest(
        Decimal("0.20"), Decimal("0.07"), AccountType.TAX_ADVANTAGED, Decimal("0")
    )
    assert result.recommendation is Recommendation.PAY_DEBT
    assert result.spread == Decimal("-0.13")
    assert result.spread < 0


def test_cheap_debt_loses_to_a_market_return() -> None:
    result = compare_debt_vs_invest(
        Decimal("0.03"), Decimal("0.07"), AccountType.TAX_ADVANTAGED, Decimal("0")
    )
    assert result.recommendation is Recommendation.INVEST
    assert result.spread == Decimal("0.04")


def test_equal_rates_are_indifferent() -> None:
    result = compare_debt_vs_invest(
        Decimal("0.07"), Decimal("0.07"), AccountType.TAX_ADVANTAGED, CGR
    )
    assert result.recommendation is Recommendation.INDIFFERENT
    assert result.spread == 0


def test_result_carries_its_inputs_and_working() -> None:
    result = compare_debt_vs_invest(
        Decimal("0.06"), Decimal("0.08"), AccountType.TAXABLE, Decimal("0.20")
    )
    assert isinstance(result, DebtVsInvestResult)
    assert result.debt_apr == Decimal("0.06")
    assert result.after_tax_return == Decimal("0.064")
    assert result.spread == result.after_tax_return - result.debt_apr


# --- R17: account type decides whether tax drag applies ---


def test_tax_advantaged_takes_the_return_whole() -> None:
    result = compare_debt_vs_invest(
        Decimal("0.05"), Decimal("0.07"), AccountType.TAX_ADVANTAGED, CGR
    )
    assert result.after_tax_return == Decimal("0.07")


def test_taxable_return_is_strictly_lower_than_tax_advantaged() -> None:
    sheltered = compare_debt_vs_invest(
        Decimal("0.05"), Decimal("0.07"), AccountType.TAX_ADVANTAGED, CGR
    )
    taxed = compare_debt_vs_invest(
        Decimal("0.05"), Decimal("0.07"), AccountType.TAXABLE, CGR
    )
    assert taxed.after_tax_return < sheltered.after_tax_return
    assert taxed.after_tax_return == Decimal("0.0595")


def test_tax_drag_can_flip_the_recommendation() -> None:
    # The same 7% return against 6% debt: worth investing untaxed, not taxed.
    sheltered = compare_debt_vs_invest(
        Decimal("0.06"), Decimal("0.07"), AccountType.TAX_ADVANTAGED, Decimal("0.30")
    )
    taxed = compare_debt_vs_invest(
        Decimal("0.06"), Decimal("0.07"), AccountType.TAXABLE, Decimal("0.30")
    )
    assert sheltered.recommendation is Recommendation.INVEST
    assert taxed.recommendation is Recommendation.PAY_DEBT


def test_zero_capital_gains_rate_leaves_a_taxable_return_whole() -> None:
    result = compare_debt_vs_invest(
        Decimal("0.05"), Decimal("0.07"), AccountType.TAXABLE, Decimal("0")
    )
    assert result.after_tax_return == Decimal("0.07")


# --- R18: validation ---


def test_negative_debt_apr_raises() -> None:
    with pytest.raises(ValueError, match="debt_apr"):
        compare_debt_vs_invest(
            Decimal("-0.01"), Decimal("0.07"), AccountType.TAXABLE, CGR
        )


def test_negative_expected_return_raises() -> None:
    with pytest.raises(ValueError, match="expected_return"):
        compare_debt_vs_invest(
            Decimal("0.05"), Decimal("-0.01"), AccountType.TAXABLE, CGR
        )


@pytest.mark.parametrize("rate", [Decimal("1"), Decimal("1.5"), Decimal("-0.1")])
def test_capital_gains_rate_outside_its_range_raises(rate: Decimal) -> None:
    with pytest.raises(ValueError, match="capital_gains_rate"):
        compare_debt_vs_invest(
            Decimal("0.05"), Decimal("0.07"), AccountType.TAXABLE, rate
        )


def test_capital_gains_rate_is_validated_even_when_unused() -> None:
    # Tax-advantaged never applies the rate, but an invalid one still fails
    # rather than waiting to take effect on a switch to taxable.
    with pytest.raises(ValueError, match="capital_gains_rate"):
        compare_debt_vs_invest(
            Decimal("0.05"), Decimal("0.07"), AccountType.TAX_ADVANTAGED, Decimal("1.4")
        )


def test_zero_rates_are_accepted() -> None:
    result = compare_debt_vs_invest(
        Decimal("0"), Decimal("0"), AccountType.TAXABLE, Decimal("0")
    )
    assert result.recommendation is Recommendation.INDIFFERENT


# --- Frozen ---


def test_result_is_frozen() -> None:
    result = compare_debt_vs_invest(
        Decimal("0.05"), Decimal("0.07"), AccountType.TAXABLE, CGR
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.spread = Decimal("1")  # type: ignore[misc]
