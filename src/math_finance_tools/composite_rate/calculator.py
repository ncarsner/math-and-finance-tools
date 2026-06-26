from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")
BIPS = Decimal("0.000001")


@dataclass(frozen=True)
class Account:
    label: str
    balance: Decimal
    apr: Decimal


@dataclass(frozen=True)
class AccountBreakdown:
    label: str
    balance: Decimal
    apr: Decimal
    monthly_interest: Decimal
    interest_share: Decimal


@dataclass(frozen=True)
class CompositeRateResult:
    composite_apr: Decimal
    monthly_interest_cost: Decimal
    per_account_breakdown: tuple[AccountBreakdown, ...]


def calculate_composite_rate(accounts: list[Account]) -> CompositeRateResult:
    total_balance = sum(a.balance for a in accounts)
    total_monthly: Decimal = sum(
        (
            (a.balance * a.apr / 12).quantize(CENTS, rounding=ROUND_HALF_UP)
            for a in accounts
        ),
        Decimal("0"),
    )

    if total_balance == 0:
        return CompositeRateResult(
            composite_apr=Decimal("0"),
            monthly_interest_cost=Decimal("0"),
            per_account_breakdown=tuple(
                AccountBreakdown(
                    label=a.label,
                    balance=a.balance,
                    apr=a.apr,
                    monthly_interest=Decimal("0"),
                    interest_share=Decimal("0"),
                )
                for a in accounts
            ),
        )

    composite_apr = (sum(a.balance * a.apr for a in accounts) / total_balance).quantize(
        BIPS, rounding=ROUND_HALF_UP
    )

    breakdown = []
    for a in accounts:
        monthly = (a.balance * a.apr / 12).quantize(CENTS, rounding=ROUND_HALF_UP)
        share = (
            (monthly / total_monthly).quantize(BIPS, rounding=ROUND_HALF_UP)
            if total_monthly != 0
            else Decimal("0")
        )
        breakdown.append(
            AccountBreakdown(
                label=a.label,
                balance=a.balance,
                apr=a.apr,
                monthly_interest=monthly,
                interest_share=share,
            )
        )

    return CompositeRateResult(
        composite_apr=composite_apr,
        monthly_interest_cost=total_monthly,
        per_account_breakdown=tuple(breakdown),
    )
