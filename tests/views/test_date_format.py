"""Date ordering follows the viewer's locale, and falls back to US ordering."""

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from views._dates import DAY_FIRST, MONTH_FIRST, YEAR_FIRST, month_label, picker_format

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "views" / "debt_payoff.py"


# --- Locale mapping ---


@pytest.mark.parametrize(
    ("locale", "expected"),
    [
        ("en-US", MONTH_FIRST),
        ("en_US", MONTH_FIRST),  # underscore form
        ("en-PH", MONTH_FIRST),
        ("en-GB", DAY_FIRST),
        ("fr-FR", DAY_FIRST),
        ("es-MX", DAY_FIRST),
        ("de-DE", DAY_FIRST),
        ("ja-JP", YEAR_FIRST),
        ("zh-Hans-CN", YEAR_FIRST),  # script subtag must not be read as a region
        ("hu-HU", YEAR_FIRST),
    ],
)
def test_region_decides_the_ordering(locale: str, expected: str) -> None:
    assert picker_format(locale) == expected


@pytest.mark.parametrize(
    ("locale", "expected"),
    [("ja", YEAR_FIRST), ("ko", YEAR_FIRST), ("fr", DAY_FIRST), ("en", MONTH_FIRST)],
)
def test_a_bare_language_still_picks_an_ordering(locale: str, expected: str) -> None:
    assert picker_format(locale) == expected


@pytest.mark.parametrize("locale", [None, ""])
def test_an_absent_locale_falls_back_to_us_ordering(locale: str | None) -> None:
    # `st.context.locale` is None whenever there is no browser at all.
    assert picker_format(locale) == MONTH_FIRST


@pytest.mark.parametrize("locale", ["not-a-locale", "xx", "sw-KE"])
def test_a_reported_but_unrecognized_locale_uses_the_worlds_majority(
    locale: str,
) -> None:
    # Something was reported and it is not US-ish, so day-first beats assuming
    # the reader shares this project's default.
    assert picker_format(locale) == DAY_FIRST


def test_a_script_subtag_is_not_mistaken_for_a_region() -> None:
    # `Hant` is four letters, so it cannot be a region; `zh` decides instead.
    assert picker_format("zh-Hant") == YEAR_FIRST


# --- Month labels carry no invented day ---


@pytest.mark.parametrize(
    ("picker", "expected"),
    [(MONTH_FIRST, "5/2035"), (DAY_FIRST, "5/2035"), (YEAR_FIRST, "2035/05")],
)
def test_month_labels_drop_the_day(picker: str, expected: str) -> None:
    # Payoff dates are normalized to the first of the month, so a day would be
    # precision the simulation does not have.
    assert month_label(date(2035, 5, 1), picker) == expected


# --- What the page actually renders ---


def test_the_pickers_use_the_resolved_format() -> None:
    at = AppTest.from_file(str(PAGE), default_timeout=90).run()
    # No browser under AppTest, so this is the fallback path end to end.
    assert at.date_input[0].proto.format == MONTH_FIRST


def test_payoff_dates_render_month_first() -> None:
    at = AppTest.from_file(str(PAGE), default_timeout=90).run()
    next(b for b in at.button if b.label == "Calculate").click().run()

    payload = at.dataframe[0].proto.arrow_data.data
    year = str(at.session_state.dp_results.snowball[0].payoff_date.year).encode()
    assert year in payload
    assert b"/" in payload  # numeric m/yyyy, not "May 2035"
