from datetime import date
from decimal import Decimal

import pytest

from math_finance_tools.debt_payoff.calculator import apply_compounding, simulate_payoff
from math_finance_tools.debt_payoff.models import CompoundingMode, Loan

START = date(2025, 1, 1)


# --- apply_compounding unit tests ---


def test_apply_compounding_monthly() -> None:
    result = apply_compounding(
        Decimal("1000"), Decimal("0.12"), CompoundingMode.MONTHLY, 30
    )
    assert result == Decimal("10.00")


def test_apply_compounding_daily_31_day_month() -> None:
    result = apply_compounding(
        Decimal("1000"), Decimal("0.12"), CompoundingMode.DAILY, 31
    )
    monthly = apply_compounding(
        Decimal("1000"), Decimal("0.12"), CompoundingMode.MONTHLY, 31
    )
    assert result > monthly


def test_apply_compounding_daily_28_day_month() -> None:
    result = apply_compounding(
        Decimal("1000"), Decimal("0.12"), CompoundingMode.DAILY, 28
    )
    monthly = apply_compounding(
        Decimal("1000"), Decimal("0.12"), CompoundingMode.MONTHLY, 28
    )
    assert result < monthly


# --- ValueError paths ---


def test_empty_loans_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        simulate_payoff([], Decimal("100"), "snowball", START)


def test_zero_balance_loan_raises() -> None:
    loan = Loan("A", Decimal("0"), Decimal("0.12"), Decimal("25"))
    with pytest.raises(ValueError, match="positive"):
        simulate_payoff([loan], Decimal("100"), "snowball", START)


def test_negative_balance_loan_raises() -> None:
    loan = Loan("A", Decimal("-500"), Decimal("0.12"), Decimal("25"))
    with pytest.raises(ValueError, match="positive"):
        simulate_payoff([loan], Decimal("100"), "snowball", START)


def test_duplicate_names_raises() -> None:
    loan_a = Loan("A", Decimal("500"), Decimal("0.12"), Decimal("25"))
    loan_b = Loan("A", Decimal("300"), Decimal("0.08"), Decimal("20"))
    with pytest.raises(ValueError, match="duplicate"):
        simulate_payoff([loan_a, loan_b], Decimal("200"), "snowball", START)


def test_budget_below_minimums_raises() -> None:
    loan = Loan("A", Decimal("500"), Decimal("0.12"), Decimal("50"))
    with pytest.raises(ValueError, match="budget"):
        simulate_payoff([loan], Decimal("40"), "snowball", START)


def test_unknown_method_raises() -> None:
    loan = Loan("A", Decimal("500"), Decimal("0.12"), Decimal("25"))
    with pytest.raises(ValueError, match="unknown method"):
        simulate_payoff([loan], Decimal("100"), "optimistic", START)


def test_max_months_exceeded_raises() -> None:
    # min_payment < monthly interest → never converges
    loan = Loan("A", Decimal("10000"), Decimal("0.24"), Decimal("10"))
    with pytest.raises(ValueError, match="converge"):
        simulate_payoff([loan], Decimal("10"), "snowball", START, max_months=2)


# --- AC2: single loan matches hand calculation ---


def test_single_loan_monthly_payoff_matches_hand_calc() -> None:
    loan = Loan("Card", Decimal("1000"), Decimal("0.12"), Decimal("25"))
    results = simulate_payoff([loan], Decimal("100"), "snowball", START)
    result = results[0]
    assert result.payoff_date == date(2025, 11, 1)
    assert result.total_interest == Decimal("58.98")
    assert result.snapshots[0].interest == Decimal("10.00")
    assert result.snapshots[0].payment == Decimal("100.00")
    assert result.snapshots[-1].remaining_balance == Decimal("0.00")


# --- AC3: snowball vs avalanche different ordering ---


def test_snowball_vs_avalanche_different_ordering() -> None:
    # Small balance + low APR vs large balance + high APR
    # Snowball targets SmallLow first (balance 300 < 500)
    # Avalanche targets BigHigh first (APR 20% > 5%)
    small_low = Loan("SmallLow", Decimal("300"), Decimal("0.05"), Decimal("15"))
    big_high = Loan("BigHigh", Decimal("500"), Decimal("0.20"), Decimal("25"))
    budget = Decimal("200")

    snowball = simulate_payoff([small_low, big_high], budget, "snowball", START)
    avalanche = simulate_payoff([small_low, big_high], budget, "avalanche", START)

    snowball_by_name = {r.loan_name: r for r in snowball}
    avalanche_by_name = {r.loan_name: r for r in avalanche}

    # Snowball pays off SmallLow first; avalanche pays off BigHigh first
    assert (
        snowball_by_name["SmallLow"].payoff_date
        <= snowball_by_name["BigHigh"].payoff_date
    )
    assert (
        avalanche_by_name["BigHigh"].payoff_date
        <= avalanche_by_name["SmallLow"].payoff_date
    )
    # The two methods produce different results
    assert (
        snowball_by_name["SmallLow"].payoff_date
        != avalanche_by_name["SmallLow"].payoff_date
    )


# --- AC4: daily compounding > monthly for long loan ---


def test_daily_compounding_exceeds_monthly_for_long_loan() -> None:
    # ~93-month loan; annual EAR daily (19.72%) > monthly (19.56%)
    loan_monthly = Loan(
        "M",
        Decimal("5000"),
        Decimal("0.18"),
        Decimal("90"),
        compounding_mode=CompoundingMode.MONTHLY,
    )
    loan_daily = Loan(
        "D",
        Decimal("5000"),
        Decimal("0.18"),
        Decimal("90"),
        compounding_mode=CompoundingMode.DAILY,
    )
    res_monthly = simulate_payoff([loan_monthly], Decimal("100"), "snowball", START)
    res_daily = simulate_payoff([loan_daily], Decimal("100"), "snowball", START)
    assert res_daily[0].total_interest > res_monthly[0].total_interest


# --- AC5: surplus cascade ---


def test_surplus_cascade_zeros_first_loan_reduces_second() -> None:
    small = Loan("Small", Decimal("100"), Decimal("0.00"), Decimal("10"))
    large = Loan("Large", Decimal("1000"), Decimal("0.12"), Decimal("50"))
    budget = Decimal("500")

    results = simulate_payoff([small, large], budget, "snowball", START)
    by_name = {r.loan_name: r for r in results}

    # Small is zeroed in month 1 (snowball targets it first)
    assert by_name["Small"].snapshots[0].remaining_balance == Decimal("0.00")
    assert len(by_name["Small"].snapshots) == 1

    # Large received cascade surplus in month 1 (payment > minimum)
    assert by_name["Large"].snapshots[0].payment > Decimal("50")


# --- AC6: grace period yields lower total interest ---


def test_grace_period_produces_lower_total_interest() -> None:
    no_grace = Loan("NoGrace", Decimal("2000"), Decimal("0.20"), Decimal("50"))
    with_grace = Loan(
        "WithGrace",
        Decimal("2000"),
        Decimal("0.20"),
        Decimal("50"),
        intro_apr=Decimal("0.00"),
        intro_end_date=date(2025, 6, 30),
    )
    res_no = simulate_payoff([no_grace], Decimal("100"), "snowball", START)
    res_grace = simulate_payoff([with_grace], Decimal("100"), "snowball", START)
    assert res_grace[0].total_interest < res_no[0].total_interest


# --- AC7: budget == sum of minimums terminates ---


def test_budget_equals_sum_of_minimums_terminates() -> None:
    # Each minimum (50) > monthly interest at peak balance (500 * 0.12/12 = 5), so amortizes
    loan = Loan("A", Decimal("500"), Decimal("0.12"), Decimal("50"))
    results = simulate_payoff([loan], Decimal("50"), "snowball", START)
    assert results[0].snapshots[-1].remaining_balance == Decimal("0.00")


# --- Tiebreak determinism ---


def test_snowball_name_tiebreak_is_deterministic() -> None:
    a = Loan("Alpha", Decimal("500"), Decimal("0.10"), Decimal("25"))
    b = Loan("Beta", Decimal("500"), Decimal("0.15"), Decimal("25"))
    r1 = simulate_payoff([a, b], Decimal("200"), "snowball", START)
    r2 = simulate_payoff([b, a], Decimal("200"), "snowball", START)
    by_name_1 = {r.loan_name: r for r in r1}
    by_name_2 = {r.loan_name: r for r in r2}
    assert by_name_1["Alpha"].payoff_date == by_name_2["Alpha"].payoff_date


# --- Grace period boundary: switches at correct month ---


def test_grace_period_boundary_month() -> None:
    # intro_end_date in January; February should use standard APR
    loan = Loan(
        "A",
        Decimal("1000"),
        Decimal("0.24"),
        Decimal("50"),
        intro_apr=Decimal("0.00"),
        intro_end_date=date(2025, 1, 31),
    )
    results = simulate_payoff([loan], Decimal("200"), "snowball", START)
    snaps = results[0].snapshots
    # January: intro_apr=0 → no interest
    assert snaps[0].interest == Decimal("0.00")
    # February: standard APR kicks in
    assert snaps[1].interest > Decimal("0.00")


# --- Results in original loan order ---


def test_results_in_original_loan_order() -> None:
    a = Loan("A", Decimal("300"), Decimal("0.05"), Decimal("15"))
    b = Loan("B", Decimal("500"), Decimal("0.20"), Decimal("25"))
    c = Loan("C", Decimal("200"), Decimal("0.10"), Decimal("10"))
    results = simulate_payoff([a, b, c], Decimal("300"), "avalanche", START)
    assert [r.loan_name for r in results] == ["A", "B", "C"]
