"""Date presentation, driven by the viewer's locale where one is available.

Streamlit's date pickers default to ``YYYY/MM/DD``, which matches almost
nobody's habit. `st.context.locale` carries the browser's language tag, so the
ordering can follow the reader instead. It is `None` whenever there is no
browser — tests, headless runs — hence the explicit fallback.

Only the *ordering* is negotiable: the picker accepts three layouts and no
others, so this maps a locale onto one of them rather than building a format
string.
"""

from datetime import date
from typing import Final

MONTH_FIRST: Final = "MM/DD/YYYY"
DAY_FIRST: Final = "DD/MM/YYYY"
YEAR_FIRST: Final = "YYYY/MM/DD"

# The month-first habit is essentially the US and territories that follow it.
MONTH_FIRST_REGIONS: Final = frozenset(
    {"US", "AS", "FM", "GU", "MH", "MP", "PH", "PR", "PW", "UM", "VI"}
)
# Year-first by convention, whether or not a region is attached to the tag.
YEAR_FIRST_REGIONS: Final = frozenset({"CN", "JP", "KR", "TW", "HU", "LT", "MN"})
YEAR_FIRST_LANGUAGES: Final = frozenset({"ja", "ko", "zh", "hu", "lt", "mn"})

# What to use when there is no locale at all. This project's reader is US-based,
# so no information means US ordering rather than the Streamlit default nobody
# asked for. A locale that *is* present but unrecognised is a different case:
# something was reported, and day-first is the world's majority habit.
FALLBACK: Final = MONTH_FIRST


def picker_format(locale: str | None) -> str:
    """One of the three layouts `st.date_input` accepts, chosen for `locale`.

    `locale` is a BCP 47 tag such as `en-US`, `en_GB` or a bare `fr`.
    """
    if not locale:
        return FALLBACK

    parts = locale.replace("_", "-").split("-")
    language = parts[0].lower()
    # The region is the first two-letter subtag after the language; anything
    # else (a script like `Hant`, a variant) is not one.
    region = next(
        (part.upper() for part in parts[1:] if len(part) == 2 and part.isalpha()),
        None,
    )

    if region in YEAR_FIRST_REGIONS:
        return YEAR_FIRST
    if region in MONTH_FIRST_REGIONS:
        return MONTH_FIRST
    if region is not None:
        return DAY_FIRST
    if language in YEAR_FIRST_LANGUAGES:
        return YEAR_FIRST
    if language == "en":
        return FALLBACK
    return DAY_FIRST


def month_label(value: date, picker: str) -> str:
    """A month-resolution date, ordered to match the picker.

    Payoff dates and snapshots are normalised to the first of the month, so the
    day carries no information — printing one would invent precision the
    simulation does not have. Month and year only; with no day in play,
    day-first and month-first readers want the same thing.
    """
    if picker == YEAR_FIRST:
        return f"{value.year}/{value.month:02d}"
    return f"{value.month}/{value.year}"
