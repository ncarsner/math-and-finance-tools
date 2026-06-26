import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from math_finance_tools.debt_payoff.models import (
    CompoundingMode,
    Loan,
    MonthlySnapshot,
    PayoffResult,
)


def test_compounding_mode_values() -> None:
    assert CompoundingMode.MONTHLY != CompoundingMode.DAILY
    assert CompoundingMode.MONTHLY.value == "monthly"
    assert CompoundingMode.DAILY.value == "daily"


def test_loan_required_fields() -> None:
    loan = Loan(
        name="Card",
        balance=Decimal("1000.00"),
        apr=Decimal("0.1999"),
        min_payment=Decimal("25.00"),
    )
    assert loan.name == "Card"
    assert loan.balance == Decimal("1000.00")
    assert loan.apr == Decimal("0.1999")
    assert loan.min_payment == Decimal("25.00")


def test_loan_compounding_mode_default() -> None:
    loan = Loan(
        name="Card",
        balance=Decimal("1000"),
        apr=Decimal("0.18"),
        min_payment=Decimal("25"),
    )
    assert loan.compounding_mode == CompoundingMode.MONTHLY


def test_loan_optional_defaults() -> None:
    loan = Loan(
        name="Card",
        balance=Decimal("1000"),
        apr=Decimal("0.18"),
        min_payment=Decimal("25"),
    )
    assert loan.intro_apr is None
    assert loan.intro_end_date is None


def test_loan_with_grace_period() -> None:
    loan = Loan(
        name="Promo Card",
        balance=Decimal("2000"),
        apr=Decimal("0.2199"),
        min_payment=Decimal("40"),
        intro_apr=Decimal("0.00"),
        intro_end_date=date(2025, 12, 31),
    )
    assert loan.intro_apr == Decimal("0.00")
    assert loan.intro_end_date == date(2025, 12, 31)


def test_loan_daily_compounding_mode() -> None:
    loan = Loan(
        name="Student Loan",
        balance=Decimal("15000"),
        apr=Decimal("0.065"),
        min_payment=Decimal("150"),
        compounding_mode=CompoundingMode.DAILY,
    )
    assert loan.compounding_mode == CompoundingMode.DAILY


def test_monthly_snapshot_fields() -> None:
    snap = MonthlySnapshot(
        loan_name="Card",
        month=date(2025, 1, 1),
        payment=Decimal("100.00"),
        interest=Decimal("15.00"),
        principal=Decimal("85.00"),
        remaining_balance=Decimal("915.00"),
    )
    assert snap.loan_name == "Card"
    assert snap.month == date(2025, 1, 1)
    assert snap.payment == Decimal("100.00")
    assert snap.interest == Decimal("15.00")
    assert snap.principal == Decimal("85.00")
    assert snap.remaining_balance == Decimal("915.00")


def test_payoff_result_fields() -> None:
    snap = MonthlySnapshot(
        loan_name="Card",
        month=date(2025, 1, 1),
        payment=Decimal("1015.00"),
        interest=Decimal("15.00"),
        principal=Decimal("1000.00"),
        remaining_balance=Decimal("0.00"),
    )
    result = PayoffResult(
        loan_name="Card",
        snapshots=(snap,),
        total_interest=Decimal("15.00"),
        payoff_date=date(2025, 1, 1),
    )
    assert result.loan_name == "Card"
    assert result.snapshots == (snap,)
    assert result.total_interest == Decimal("15.00")
    assert result.payoff_date == date(2025, 1, 1)


def test_monthly_snapshot_frozen() -> None:
    snap = MonthlySnapshot(
        loan_name="Card",
        month=date(2025, 1, 1),
        payment=Decimal("100"),
        interest=Decimal("15"),
        principal=Decimal("85"),
        remaining_balance=Decimal("915"),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.payment = Decimal("200")  # type: ignore[misc]


def test_payoff_result_frozen() -> None:
    result = PayoffResult(
        loan_name="Card",
        snapshots=(),
        total_interest=Decimal("0"),
        payoff_date=date(2025, 1, 1),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.loan_name = "Other"  # type: ignore[misc]
