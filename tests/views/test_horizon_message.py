"""The Debt Payoff page reports an unpayable budget in plain language."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[2] / "views" / "debt_payoff.py"


def test_impossible_budget_reports_the_budget_that_clears() -> None:
    at = AppTest.from_file(str(PAGE), default_timeout=60).run()
    at.number_input[1].set_value(30.0).run()  # $5000 at 30% against $100/month
    next(b for b in at.button if b.label == "Calculate").click().run()

    [message] = [e.value for e in at.error]
    assert "Impossible at this budget" in message
    assert "converge" not in message
    assert "would clear them within ten years" in message
    assert not at.dataframe
