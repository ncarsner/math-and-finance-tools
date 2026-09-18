"""The Debt vs. Invest page: reactive, prefilled from Composite Rate."""

import re
from decimal import Decimal
from pathlib import Path

from streamlit.testing.v1 import AppTest

from math_finance_tools.composite_rate import Account, calculate_composite_rate

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "views" / "debt_vs_invest.py"
COMPOSITE_PAGE = ROOT / "views" / "composite_rate.py"
ENTRY = ROOT / "Home.py"

TAXABLE = "Taxable brokerage"


def _page() -> AppTest:
    return AppTest.from_file(str(PAGE), default_timeout=60).run()


def _labels(at: AppTest) -> list[str]:
    return [n.label for n in at.number_input]


def _metric(at: AppTest, label: str) -> str:
    return next(m.proto.body for m in at.get("metric") if m.proto.label == label)


# --- R26: registered, and reactive with no button ---


def test_all_four_calculators_are_registered() -> None:
    source = ENTRY.read_text()
    titles = re.findall(r'st\.Page\("(views/[^"]+)", title="([^"]+)"', source)
    assert [title for _, title in titles] == [
        "Home",
        "Debt Payoff Calculator",
        "Composite Rate Calculator",
        "Debt vs. Invest",
    ]
    for page_path, _ in titles:
        assert (ROOT / page_path).exists()


def test_result_updates_without_a_button_press() -> None:
    at = _page()
    assert not at.button
    assert "Pay down the debt" in at.success[0].value

    at.number_input[1].set_value(25.0).run()  # expected return

    assert not at.button
    assert "Invest" in at.success[0].value
    assert at.session_state.filtered_state == {}  # nothing stored between runs


# --- R27: inputs, and the capital-gains field only under TAXABLE ---


def test_capital_gains_field_appears_only_for_a_taxable_account() -> None:
    at = _page()
    assert _labels(at) == ["Debt APR (%)", "Expected annual return (%)"]

    at.radio[0].set_value(TAXABLE).run()
    assert _labels(at)[2] == "Capital gains rate (%)"
    assert at.number_input[2].value == 15.0

    at.radio[0].set_value("Tax-advantaged (401(k), IRA, HSA)").run()
    assert "Capital gains rate (%)" not in _labels(at)


def test_percentages_convert_to_the_fractions_the_calculator_expects() -> None:
    at = _page()
    at.number_input[0].set_value(6.0).run()  # debt APR
    at.number_input[1].set_value(7.0).run()  # expected return
    at.radio[0].set_value(TAXABLE).run()
    at.number_input[2].set_value(20.0).run()  # capital gains rate

    # 7% taxed at 20% is 5.6%, which loses to 6% debt
    assert _metric(at, "After-tax return") == "5.60%"
    assert _metric(at, "Spread") == "-0.40 pts"
    assert "Pay down the debt" in at.success[0].value


def test_debt_apr_label_says_it_is_taken_after_any_deduction() -> None:
    at = _page()
    assert "after any tax deduction" in at.number_input[0].help


# --- R28: the one-directional handoff from Composite Rate ---


def test_composite_rate_publishes_its_apr_to_a_plain_key() -> None:
    at = AppTest.from_file(str(COMPOSITE_PAGE), default_timeout=60).run()

    # The default accounts are $5,000 at 18% and $3,000 at 12%
    expected = (
        float(
            calculate_composite_rate(
                [
                    Account("Account 1", Decimal("5000"), Decimal("0.18")),
                    Account("Account 2", Decimal("3000"), Decimal("0.12")),
                ]
            ).composite_apr
        )
        * 100
    )
    assert at.session_state["shared_composite_apr"] == expected

    # Navigating is modelled by a fresh run seeded with the surviving keys:
    # Streamlit drops the widget-keyed entries and keeps the plain one, so the
    # rate arrives on the other page.
    onward = AppTest.from_file(str(PAGE), default_timeout=60)
    for key, value in at.session_state.filtered_state.items():
        if not key.startswith("cr_"):
            onward.session_state[key] = value
    onward.run()

    assert onward.number_input[0].value == expected


def test_debt_apr_is_prefilled_from_the_composite_rate_and_stays_editable() -> None:
    at = AppTest.from_file(str(PAGE), default_timeout=60)
    at.session_state["shared_composite_apr"] = 15.75
    at.run()

    assert at.number_input[0].value == 15.75

    at.number_input[0].set_value(4.0).run()
    assert at.number_input[0].value == 4.0
    assert at.session_state["shared_composite_apr"] == 15.75  # never written back


def test_debt_apr_falls_back_to_a_default_without_a_composite_rate() -> None:
    at = _page()
    assert "shared_composite_apr" not in at.session_state
    assert at.number_input[0].value == 18.0


# --- R29: every recommendation renders ---


def test_indifference_is_reported_when_the_rates_match() -> None:
    at = _page()
    at.number_input[0].set_value(7.0).run()
    at.number_input[1].set_value(7.0).run()

    assert "**Either.**" in at.success[0].value
    assert _metric(at, "Spread") == "+0.00 pts"
    assert _metric(at, "After-tax return") == "7.00%"


def test_investing_wins_against_cheap_debt() -> None:
    at = _page()
    at.number_input[0].set_value(3.0).run()

    assert "**Invest.**" in at.success[0].value
    assert _metric(at, "Spread") == "+4.00 pts"
    assert _metric(at, "Debt APR") == "3.00%"
