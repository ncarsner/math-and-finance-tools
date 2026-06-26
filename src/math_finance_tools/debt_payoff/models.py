from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


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
