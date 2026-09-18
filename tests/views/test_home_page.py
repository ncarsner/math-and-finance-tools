"""The Home page introduces every calculator in the nav."""

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "views" / "home.py"
ENTRY = ROOT / "Home.py"


def _page() -> AppTest:
    return AppTest.from_file(str(PAGE), default_timeout=60).run()


def test_every_calculator_in_the_nav_has_a_section() -> None:
    source = ENTRY.read_text()
    nav_titles = re.findall(r'st\.Page\("views/[^"]+", title="([^"]+)"', source)
    calculators = [title for title in nav_titles if title != "Home"]

    assert [h.value for h in _page().subheader] == calculators


def test_each_section_points_at_the_sidebar() -> None:
    at = _page()
    pointers = [m.value for m in at.markdown if m.value.startswith("Select **")]
    assert pointers == [
        "Select **Debt Payoff Calculator** in the sidebar to get started.",
        "Select **Composite Rate Calculator** in the sidebar to get started.",
        "Select **Debt vs. Invest** in the sidebar to get started.",
    ]


def test_debt_payoff_section_covers_the_verdict_and_the_additional_payment() -> None:
    body = " ".join(m.value for m in _page().markdown)
    assert "names the winning strategy" in body
    assert "what paying more would buy" in body


def test_debt_vs_invest_section_names_what_it_decides() -> None:
    body = " ".join(m.value for m in _page().markdown)
    assert "after tax" in body
    assert "composite" in body
