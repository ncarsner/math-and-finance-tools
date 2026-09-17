from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal


class HorizonExceededError(ValueError):
    """The debt cannot be cleared within the simulation horizon at this budget."""


class CompoundingMode(Enum):
    MONTHLY = "monthly"
    DAILY = "daily"


@dataclass(frozen=True)
class Loan:
    name: str
    balance: Decimal
    apr: Decimal
    min_payment: Decimal
    compounding_mode: CompoundingMode = CompoundingMode.MONTHLY
    intro_apr: Decimal | None = None
    intro_end_date: date | None = None


@dataclass(frozen=True)
class MonthlySnapshot:
    loan_name: str
    month: date
    payment: Decimal
    interest: Decimal
    principal: Decimal
    remaining_balance: Decimal


@dataclass(frozen=True)
class PayoffResult:
    loan_name: str
    snapshots: tuple[MonthlySnapshot, ...]
    total_interest: Decimal
    payoff_date: date


@dataclass(frozen=True)
class AvalancheOutcome:
    results: tuple[PayoffResult, ...]
    ordering: Literal["static", "effective"]
    total_interest: Decimal


@dataclass(frozen=True)
class StrategyVerdict:
    """Snowball against the better avalanche ordering, with a winner always named.

    Month counts are inclusive of the start month. `months_delta` is the loser's
    total duration minus the winner's, so it is negative when the cheaper
    strategy takes longer.
    """

    winner: Literal["snowball", "avalanche"]
    winner_total_interest: Decimal
    loser_total_interest: Decimal
    interest_delta: Decimal
    months_delta: int
    snowball_first_clear_months: int
    avalanche_first_clear_months: int
    avalanche_ordering: Literal["static", "effective"]
    snowball: tuple[PayoffResult, ...]
    avalanche: AvalancheOutcome
