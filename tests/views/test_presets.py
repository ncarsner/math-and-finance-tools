"""The worked examples: each one must actually show a disagreement."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from math_finance_tools.debt_payoff import (
    CompoundingMode,
    HorizonExceededError,
    Loan,
    compare_strategies,
)
from views._presets import PRESETS, Preset, _end_of_month, loan_values

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "views" / "debt_payoff.py"

HORIZON_PRESET = "Budget too tight to clear"
CLEARING_PRESETS = [name for name in PRESETS if name != HORIZON_PRESET]


def _page() -> AppTest:
    return AppTest.from_file(str(PAGE), default_timeout=90).run()


def _button(at: AppTest, label: str):  # type: ignore[no-untyped-def]
    return next(b for b in at.button if b.label == label)


def _as_loans(preset: Preset, start: date) -> list[Loan]:
    """Mirror the page's own conversion from stored values to `Loan`s."""
    return [
        Loan(
            name=v["name"],
            balance=Decimal(str(v["balance"])),
            apr=Decimal(str(v["apr"])) / 100,
            min_payment=Decimal(str(v["min"])),
            compounding_mode=(
                CompoundingMode.DAILY
                if v["comp"] == "Daily"
                else CompoundingMode.MONTHLY
            ),
            intro_apr=Decimal(str(v["intro_apr"])) / 100 if v["grace"] else None,
            intro_end_date=v["intro_end"] if v["grace"] else None,
        )
        for v in loan_values(preset, start)
    ]


# --- The point of the presets: the strategies must differ ---


@pytest.mark.parametrize("name", CLEARING_PRESETS)
def test_preset_makes_the_two_strategies_disagree(name: str) -> None:
    preset = PRESETS[name]
    start = date.today()
    verdict = compare_strategies(
        _as_loans(preset, start), Decimal(str(preset.budget)), start
    )
    snowball_interest = sum(r.total_interest for r in verdict.snowball)

    # Identical totals mean both orderings paid the same loans in the same
    # sequence — the overlapping-traces case these examples exist to avoid.
    assert snowball_interest != verdict.avalanche.total_interest
    assert verdict.interest_delta > 0


@pytest.mark.parametrize("name", CLEARING_PRESETS)
def test_preset_budget_is_payable_and_below_its_ceiling(name: str) -> None:
    preset = PRESETS[name]
    assert preset.budget >= preset.sum_minimums
    assert preset.ceiling >= preset.budget


def test_the_promotional_preset_is_won_by_the_rate_aware_ordering() -> None:
    preset = PRESETS["Promotional rates in play"]
    start = date.today()
    verdict = compare_strategies(
        _as_loans(preset, start), Decimal(str(preset.budget)), start
    )
    assert verdict.avalanche_ordering == "effective"


def test_the_tight_budget_preset_overruns_the_horizon() -> None:
    preset = PRESETS[HORIZON_PRESET]
    start = date.today()
    with pytest.raises(HorizonExceededError):
        compare_strategies(_as_loans(preset, start), Decimal(str(preset.budget)), start)


# --- Intro dates are relative, so an example does not expire ---


def test_intro_end_dates_are_relative_to_the_start() -> None:
    preset = PRESETS["Promotional rates in play"]
    early = loan_values(preset, date(2030, 1, 15))
    later = loan_values(preset, date(2040, 1, 15))

    assert early[0]["intro_end"].year == 2032  # start + 30 months
    assert later[0]["intro_end"].year == 2042
    assert early[0]["grace"] is True
    assert early[2]["grace"] is False  # no intro APR on the plain card


@pytest.mark.parametrize(
    ("months", "expected"),
    [
        (0, date(2027, 1, 31)),
        (1, date(2027, 2, 28)),
        (11, date(2027, 12, 31)),
        (12, date(2028, 1, 31)),
        (25, date(2029, 2, 28)),
    ],
)
def test_end_of_month_rolls_the_year_over(months: int, expected: date) -> None:
    assert _end_of_month(date(2027, 1, 10), months) == expected


# --- Loading one through the page ---


def test_loading_a_preset_replaces_the_loans_and_the_budget() -> None:
    at = _page()
    assert len(at.session_state.dp_loan_ids) == 1  # the stock single loan

    _button(at, "Load this example").click().run()

    preset = PRESETS[next(iter(PRESETS))]
    names = [
        at.session_state.dp_loan_values[i]["name"] for i in at.session_state.dp_loan_ids
    ]
    assert names == [loan.name for loan in preset.loans]
    assert at.session_state.dp_monthly_budget == preset.budget
    assert at.session_state.dp_additional_budget == preset.additional


def test_loading_a_preset_discards_a_previous_result() -> None:
    at = _page()
    _button(at, "Calculate").click().run()
    assert "dp_results" in at.session_state

    _button(at, "Load this example").click().run()
    assert "dp_results" not in at.session_state
    assert "dp_extra" not in at.session_state


def test_a_loaded_preset_overwrites_what_the_user_typed() -> None:
    at = _page()
    at.text_input(key="dp_name_0").set_value("My own loan").run()
    at.number_input(key="dp_balance_0").set_value(999.0).run()

    _button(at, "Load this example").click().run()

    # The rendered widgets must show the preset, not the typed-over entry: a
    # keyed widget outranks its own `value=`, so reusing row IDs would leave
    # "My own loan" on screen while the stored values said otherwise.
    rendered = [t.value for t in at.text_input]
    preset = PRESETS[next(iter(PRESETS))]
    assert rendered == [loan.name for loan in preset.loans]
    assert "My own loan" not in rendered
    assert at.number_input(
        key=f"dp_balance_{at.session_state.dp_loan_ids[0]}"
    ).value == (preset.loans[0].balance)


def test_the_loaded_example_charts_two_separated_strategies() -> None:
    at = _page()
    at.selectbox(key="dp_preset_choice").set_value("Avalanche saves the most").run()
    _button(at, "Load this example").click().run()
    _button(at, "Calculate").click().run()

    traces = json.loads(at.get("plotly_chart")[0].proto.spec)["data"]
    by_name = {t["name"]: t["y"] for t in traces}
    snowball = next(
        v for k, v in by_name.items() if k.startswith("Snowball") and "+" not in k
    )
    avalanche = next(
        v for k, v in by_name.items() if k.startswith("Avalanche") and "+" not in k
    )

    assert snowball != avalanche  # the overlap the examples exist to fix


def test_the_tight_budget_example_tells_the_user_it_cannot_be_done() -> None:
    at = _page()
    at.selectbox(key="dp_preset_choice").set_value(HORIZON_PRESET).run()
    _button(at, "Load this example").click().run()
    _button(at, "Calculate").click().run()

    assert "Impossible at this budget" in at.error[0].value
    assert "would clear them" in at.error[0].value
    assert "dp_results" not in at.session_state
