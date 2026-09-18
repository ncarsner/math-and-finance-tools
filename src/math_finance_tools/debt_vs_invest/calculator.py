from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class AccountType(Enum):
    """Whether a return suffers annual tax drag at all."""

    TAX_ADVANTAGED = "tax_advantaged"
    TAXABLE = "taxable"


class Recommendation(Enum):
    PAY_DEBT = "pay_debt"
    INVEST = "invest"
    INDIFFERENT = "indifferent"


@dataclass(frozen=True)
class DebtVsInvestResult:
    debt_apr: Decimal
    after_tax_return: Decimal
    spread: Decimal
    recommendation: Recommendation


def compare_debt_vs_invest(
    debt_apr: Decimal,
    expected_return: Decimal,
    account_type: AccountType,
    capital_gains_rate: Decimal,
) -> DebtVsInvestResult:
    """Compare a debt rate against an after-tax expected return.

    Both sides are nominal: inflation applies to each equally and cancels in
    the spread, so an inflation input would change neither the figure nor the
    recommendation. `debt_apr` is the rate after any tax deduction the
    borrower actually takes, which is the caller's to determine.
    """
    if debt_apr < 0:
        raise ValueError("debt_apr must not be negative")
    if expected_return < 0:
        raise ValueError("expected_return must not be negative")
    # Validated under both account types: a rate of 1.4 sitting unused in a
    # tax-advantaged call is still wrong, and would take effect the moment the
    # caller switched to taxable.
    if not 0 <= capital_gains_rate < 1:
        raise ValueError("capital_gains_rate must be in [0, 1)")

    if account_type == AccountType.TAX_ADVANTAGED:
        after_tax_return = expected_return
    else:
        after_tax_return = expected_return * (1 - capital_gains_rate)

    spread = after_tax_return - debt_apr
    if spread > 0:
        recommendation = Recommendation.INVEST
    elif spread < 0:
        recommendation = Recommendation.PAY_DEBT
    else:
        recommendation = Recommendation.INDIFFERENT

    return DebtVsInvestResult(
        debt_apr=debt_apr,
        after_tax_return=after_tax_return,
        spread=spread,
        recommendation=recommendation,
    )
