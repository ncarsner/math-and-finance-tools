"""The Debt Payoff page names a winner above the comparison table."""

from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[2] / "views" / "debt_payoff.py"


def _page() -> AppTest:
    return AppTest.from_file(str(PAGE), default_timeout=60).run()


def _calculate(at: AppTest) -> AppTest:
    return next(b for b in at.button if b.label == "Calculate").click().run()


def test_verdict_names_avalanche_with_dollar_and_month_deltas() -> None:
    at = _page()
    next(b for b in at.button if b.label == "+ Add Loan").click().run()

    at.number_input[0].set_value(1000.0).run()  # small loan, low rate
    at.number_input[1].set_value(5.0).run()
    at.number_input[2].set_value(25.0).run()
    at.number_input[3].set_value(5000.0).run()  # big loan, high rate
    at.number_input[4].set_value(20.0).run()
    at.number_input[5].set_value(100.0).run()
    at.number_input[6].set_value(20000.0).run()  # budget ceiling
    at.date_input[0].set_value(date(2026, 1, 1)).run()
    at.slider[0].set_value(400.0).run()
    _calculate(at)

    assert not at.error
    [verdict] = [s.value for s in at.success]
    assert verdict == (
        "**Avalanche (rate order)** saves **$166.71** in interest "
        "and finishes 1 month sooner."
    )

    subheaders = [h.value for h in at.subheader]
    assert subheaders.index("Verdict") < subheaders.index("Comparison")

    # Column names live in the Arrow schema of the table payload
    assert b"First loan cleared" in at.dataframe[0].proto.arrow_data.data


def test_tie_is_still_named_for_snowball() -> None:
    at = _page()
    at.number_input[3].set_value(20000.0).run()  # budget ceiling
    at.slider[0].set_value(800.0).run()
    _calculate(at)

    [verdict] = [s.value for s in at.success]
    assert verdict == (
        "**Snowball (lowest balance first)** — both strategies cost $290.83 in "
        "interest, and both clear their first loan in the same month, so the tie "
        "goes to snowball."
    )
