"""Worked examples for the Debt Payoff page.

Each preset is a loan set chosen so the two strategies visibly disagree. A set
whose balance order matches its rate order makes snowball and avalanche pay the
same loans in the same sequence, so the rows report identical totals and the
chart traces sit on top of one another — true, but it teaches nothing. Every
preset here inverts that order somewhere, or puts a promotional rate in play.

Not a page: `views/` holds the explicit `st.navigation` list, and this module is
imported by `debt_payoff.py` rather than registered.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class PresetLoan:
    name: str
    balance: float
    apr: float
    min_payment: float
    compounding: str = "Monthly"
    intro_apr: float | None = None
    # Months from the simulation start, so an example stays meaningful whenever
    # it is loaded rather than expiring against a hardcoded calendar date.
    intro_end_months: int | None = None


@dataclass(frozen=True)
class Preset:
    summary: str
    takeaway: str
    budget: float
    additional: float
    loans: tuple[PresetLoan, ...]

    @property
    def sum_minimums(self) -> float:
        return sum(loan.min_payment for loan in self.loans)

    @property
    def ceiling(self) -> float:
        """Headroom above the budget so the slider can be dragged both ways."""
        return max(self.budget + 500.0, self.sum_minimums * 2)


def _end_of_month(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, monthrange(year, month)[1])


def loan_values(preset: Preset, start: date) -> list[dict[str, Any]]:
    """The preset as the page's own `dp_loan_values` payloads."""
    return [
        {
            "name": loan.name,
            "balance": loan.balance,
            "apr": loan.apr,
            "min": loan.min_payment,
            "comp": loan.compounding,
            "grace": loan.intro_apr is not None,
            "intro_apr": loan.intro_apr or 0.0,
            "intro_end": (
                _end_of_month(start, loan.intro_end_months)
                if loan.intro_end_months is not None
                else start
            ),
        }
        for loan in preset.loans
    ]


PRESETS: dict[str, Preset] = {
    "Avalanche saves the most": Preset(
        summary=(
            "A big card at 26.9% sits behind two cheaper, smaller debts. Paying "
            "by balance clears the small ones first and leaves the expensive "
            "one accruing."
        ),
        takeaway="Rate order wins by roughly $2,900 and three months.",
        budget=900.0,
        additional=150.0,
        loans=(
            PresetLoan("Store card", 1200.0, 6.9, 40.0),
            PresetLoan("Auto loan", 9000.0, 5.9, 220.0),
            PresetLoan("Credit card", 15000.0, 26.9, 380.0),
        ),
    ),
    "Snowball buys an early win": Preset(
        summary=(
            "A small interest-free medical bill against one large card. "
            "Snowball clears a debt in month 3; avalanche takes until month 16."
        ),
        takeaway="That early win costs under $200 — momentum is nearly free here.",
        budget=700.0,
        additional=100.0,
        loans=(
            PresetLoan("Medical bill", 800.0, 0.0, 50.0),
            PresetLoan("Credit card", 18000.0, 22.9, 400.0),
        ),
    ),
    "Promotional rates in play": Preset(
        summary=(
            "Two transferred balances on intro rates that expire at different "
            "times. Ordering by the go-to rate attacks a balance that is "
            "currently costing almost nothing."
        ),
        takeaway=(
            "The promotional-rate aware ordering wins — this is the case the "
            "best-of-two avalanche exists for."
        ),
        budget=850.0,
        additional=150.0,
        loans=(
            PresetLoan(
                "Transfer A", 10000.0, 26.9, 200.0, intro_apr=2.9, intro_end_months=30
            ),
            PresetLoan(
                "Transfer B", 6000.0, 15.9, 130.0, intro_apr=0.0, intro_end_months=12
            ),
            PresetLoan("Credit card", 7500.0, 23.9, 190.0),
        ),
    ),
    "Student loan, daily compounding": Preset(
        summary=(
            "A large student loan compounding daily at a middling rate, behind "
            "a cheap car loan and an expensive card."
        ),
        takeaway="Rate order still wins, and the daily loan costs more than its APR suggests.",
        budget=850.0,
        additional=150.0,
        loans=(
            PresetLoan("Car loan", 4000.0, 3.9, 130.0),
            PresetLoan("Credit card", 6000.0, 22.9, 150.0),
            PresetLoan("Student loan", 26000.0, 7.2, 280.0, compounding="Daily"),
        ),
    ),
    "Budget too tight to clear": Preset(
        summary=(
            "Three high-rate balances against a budget barely above the sum of "
            "the minimums."
        ),
        takeaway=(
            "Neither strategy clears inside ten years — the page says so and "
            "names the budget that would."
        ),
        budget=1080.0,
        additional=0.0,
        loans=(
            PresetLoan("Credit card 1", 21000.0, 27.9, 470.0),
            PresetLoan("Credit card 2", 15000.0, 26.4, 340.0),
            PresetLoan("Personal loan", 11000.0, 15.9, 250.0),
        ),
    ),
}
