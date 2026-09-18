"""The Debt Payoff page shows what an additional monthly payment buys."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[2] / "views" / "debt_payoff.py"


def _page() -> AppTest:
    return AppTest.from_file(str(PAGE), default_timeout=60).run()


def _calculate(at: AppTest) -> AppTest:
    return next(b for b in at.button if b.label == "Calculate").click().run()


def _traces(at: AppTest) -> list[str]:
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    return [trace["name"] for trace in spec["data"]]


def _two_loans(at: AppTest) -> AppTest:
    """The lower balance at the lower rate, so the strategies disagree."""
    next(b for b in at.button if b.label == "+ Add Loan").click().run()
    at.number_input[0].set_value(1000.0).run()
    at.number_input[1].set_value(5.0).run()
    at.number_input[2].set_value(25.0).run()
    at.number_input[3].set_value(5000.0).run()
    at.number_input[4].set_value(20.0).run()
    at.number_input[5].set_value(100.0).run()
    at.number_input[6].set_value(20000.0).run()  # budget ceiling
    at.date_input[0].set_value(date(2026, 1, 1)).run()
    return at.slider[0].set_value(400.0).run()


def test_zero_additional_payment_renders_nothing_extra() -> None:
    at = _page()
    at.number_input[3].set_value(20000.0).run()
    at.slider[0].set_value(400.0).run()
    _calculate(at)

    assert at.number_input[4].value == 0.0  # the field defaults to zero
    assert "dp_extra" not in at.session_state
    assert not [h.value for h in at.subheader if h.value.startswith("Adding ")]
    assert len(_traces(at)) == 2


def test_additional_payment_saves_months_and_interest_per_strategy() -> None:
    at = _two_loans(_page())
    at.number_input[7].set_value(200.0).run()  # additional monthly payment
    _calculate(at)

    assert not at.error
    subheaders = [h.value for h in at.subheader]
    assert "Adding $200 a Month" in subheaders
    assert subheaders.index("Comparison") < subheaders.index("Adding $200 a Month")

    extra = at.session_state["dp_extra"]
    assert extra["snowball"].months_saved == 7
    assert extra["snowball"].interest_saved == Decimal("330.48")
    assert extra["avalanche"].months_saved == 6
    assert extra["avalanche"].interest_saved == Decimal("272.16")

    # The savings table is the second one on the page, after the comparison
    payload = at.dataframe[1].proto.arrow_data.data
    assert b"Months saved" in payload
    assert b"Interest saved" in payload
    assert b"Snowball (lowest balance first)" in payload
    assert b"Avalanche (rate order)" in payload


def test_additional_payment_charts_four_traces() -> None:
    at = _two_loans(_page())
    at.number_input[7].set_value(200.0).run()
    _calculate(at)

    assert _traces(at) == [
        "Snowball (lowest balance first)",
        "Avalanche (rate order)",
        "Snowball (lowest balance first) + $200",
        "Avalanche (rate order) + $200",
    ]


def test_returning_to_zero_clears_the_section() -> None:
    at = _two_loans(_page())
    at.number_input[7].set_value(200.0).run()
    _calculate(at)
    assert "dp_extra" in at.session_state

    at.number_input[7].set_value(0.0).run()
    _calculate(at)

    assert "dp_extra" not in at.session_state
    assert not [h.value for h in at.subheader if h.value.startswith("Adding ")]
    assert len(_traces(at)) == 2


def test_changing_a_loan_drops_the_stored_comparison() -> None:
    at = _two_loans(_page())
    at.number_input[7].set_value(200.0).run()
    _calculate(at)
    assert "dp_extra" in at.session_state

    next(b for b in at.button if b.label == "+ Add Loan").click().run()

    assert "dp_extra" not in at.session_state
    assert "dp_results" not in at.session_state
