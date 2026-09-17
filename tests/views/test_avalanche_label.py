"""The avalanche row names the ordering that actually won."""

from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[2] / "views" / "debt_payoff.py"


def _page() -> AppTest:
    return AppTest.from_file(str(PAGE), default_timeout=60).run()


def _calculate(at: AppTest) -> AppTest:
    return next(b for b in at.button if b.label == "Calculate").click().run()


def test_plain_loans_report_rate_order() -> None:
    at = _page()
    at.number_input[3].set_value(20000.0).run()  # budget ceiling
    at.slider[0].set_value(800.0).run()
    _calculate(at)

    labels = [e.label for e in at.expander]
    assert "Avalanche (rate order)" in labels
    assert "Avalanche (promotional-rate aware)" not in labels


def test_lasting_promo_reports_the_promotional_rate_aware_ordering() -> None:
    at = _page()
    next(b for b in at.button if b.label == "+ Add Loan").click().run()

    at.number_input[0].set_value(4000.0).run()  # loan 1 balance
    at.number_input[1].set_value(29.0).run()  # loan 1 APR
    at.number_input[2].set_value(50.0).run()  # loan 1 minimum
    at.checkbox[0].set_value(True).run()  # loan 1 grace period
    at.number_input[3].set_value(0.0).run()  # intro APR
    at.date_input[0].set_value(date(2030, 1, 1)).run()  # intro end

    at.number_input[4].set_value(4000.0).run()  # loan 2 balance
    at.number_input[5].set_value(12.0).run()
    at.number_input[6].set_value(50.0).run()

    at.number_input[7].set_value(20000.0).run()  # budget ceiling
    at.date_input[1].set_value(date(2026, 1, 1)).run()  # simulation start
    at.slider[0].set_value(500.0).run()
    _calculate(at)

    assert not at.error
    labels = [e.label for e in at.expander]
    assert "Avalanche (promotional-rate aware)" in labels
    assert "Avalanche (rate order)" not in labels
