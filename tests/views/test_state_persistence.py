"""Regression tests for the page-navigation state loss and stale results.

Streamlit deletes every widget-associated session-state entry when a page
stops rendering, while plain keys survive. `_navigate` models exactly that:
a fresh run of the page seeded with only the keys navigation would preserve.
"""

import re
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

VIEWS = Path(__file__).resolve().parents[2] / "views"

WIDGET_KEY = re.compile(
    r"^(dp_(name|balance|apr|min|comp|grace|intro_apr|intro_end|remove)_\d+"
    r"|cr_(label|balance|apr|remove)_\d+)$"
)


def _run(page: str) -> AppTest:
    return AppTest.from_file(str(VIEWS / page), default_timeout=60).run()


def _navigate(page: str, at: AppTest) -> AppTest:
    """Leave the page and come back."""
    fresh = AppTest.from_file(str(VIEWS / page), default_timeout=60)
    for key, value in dict(at.session_state.filtered_state).items():
        if not WIDGET_KEY.match(key):
            fresh.session_state[key] = value
    return fresh.run()


def _calculate(at: AppTest) -> AppTest:
    button = next(b for b in at.button if b.label == "Calculate")
    return button.click().run()


def test_debt_payoff_loans_survive_navigation() -> None:
    at = _run("debt_payoff.py")
    at.text_input[0].set_value("Visa").run()
    at.number_input[0].set_value(7500.0).run()

    returned = _navigate("debt_payoff.py", at)

    assert not returned.exception
    assert returned.text_input[0].value == "Visa"
    assert returned.number_input[0].value == pytest.approx(7500.0)


def test_composite_rate_accounts_survive_navigation() -> None:
    at = _run("composite_rate.py")
    at.number_input[0].set_value(9000.0).run()
    composite_before: Any = at.metric[0].value

    returned = _navigate("composite_rate.py", at)

    assert not returned.exception
    assert returned.number_input[0].value == pytest.approx(9000.0)
    assert returned.metric[0].value == composite_before


def test_failed_calculate_clears_previous_results() -> None:
    at = _run("debt_payoff.py")
    at.number_input[3].set_value(20000.0).run()  # budget ceiling
    at.slider[0].set_value(800.0).run()  # comfortably affordable
    _calculate(at)

    assert not at.error
    assert at.dataframe, "an affordable budget should produce results"

    at.number_input[1].set_value(30.0).run()  # APR the minimum cannot outrun
    at.slider[0].set_value(100.0).run()  # budget = sum of minimums
    _calculate(at)

    assert at.error, "an unpayable budget should report an error"
    assert not at.dataframe, "the previous run's results must not remain on screen"
