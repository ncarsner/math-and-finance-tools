"""The README has to keep up with what the app actually ships."""

import re
from pathlib import Path

from views._presets import PRESETS

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
ENTRY = (ROOT / "Home.py").read_text()


def _nav_calculators() -> list[str]:
    titles = re.findall(r'st\.Page\("views/[^"]+", title="([^"]+)"', ENTRY)
    return [title for title in titles if title != "Home"]


def test_every_calculator_in_the_nav_has_a_readme_section() -> None:
    headings = re.findall(r"^### (.+)$", README, re.M)
    assert headings == _nav_calculators()


def test_every_worked_example_is_listed() -> None:
    for name in PRESETS:
        assert name in README, (
            f"{name} is loadable in the app but absent from the README"
        )


def test_the_documented_commands_are_the_ones_that_work() -> None:
    # `mypy` is not on PATH in this project; it runs through uv like pytest.
    assert "uv run mypy src/" in README
    assert "uv run pytest --cov=src" in README
    # Lint and format must cover tests/ too, or the suite can drift out of style.
    for command in ("ruff format", "ruff check"):
        line = next(ln for ln in README.splitlines() if ln.startswith(command))
        assert "tests/" in line and "views/" in line and "Home.py" in line
