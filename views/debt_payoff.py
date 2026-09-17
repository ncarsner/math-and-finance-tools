from collections import defaultdict
from datetime import date
from decimal import ROUND_CEILING, Decimal
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from math_finance_tools.debt_payoff import (
    CompoundingMode,
    HorizonExceededError,
    Loan,
    minimum_budget_to_clear,
    simulate_payoff,
)

st.title("Debt Payoff Calculator")

COMPOUNDING_OPTIONS = ["Monthly", "Daily"]

# ── Session state initialisation ─────────────────────────────────────────────
#
# Streamlit deletes every widget-associated session-state entry when a page
# stops rendering, so widget keys cannot be the store. Entered values live in
# `dp_loan_values`, a plain key that survives navigation; the widget keys are
# treated as disposable and reseeded from it on every run.


def _loan_defaults(n: int) -> dict[str, Any]:
    return {
        "name": f"Loan {n}",
        "balance": 1000.0,
        "apr": 10.0,
        "min": 25.0,
        "comp": "Monthly",
        "grace": False,
        "intro_apr": 0.0,
        "intro_end": date.today(),
    }


if "dp_loan_ids" not in st.session_state:
    st.session_state.dp_loan_ids: list[int] = [0]
    st.session_state.dp_next_id: int = 1
    st.session_state.dp_loan_values: dict[int, dict[str, Any]] = {
        0: _loan_defaults(1) | {"balance": 5000.0, "apr": 18.0, "min": 100.0}
    }


def add_loan() -> None:
    new_id: int = st.session_state.dp_next_id
    st.session_state.dp_next_id += 1
    st.session_state.dp_loan_values[new_id] = _loan_defaults(
        len(st.session_state.dp_loan_ids) + 1
    )
    st.session_state.dp_loan_ids.append(new_id)
    st.session_state.pop("dp_results", None)


def remove_loan(loan_id: int) -> None:
    st.session_state.dp_loan_ids.remove(loan_id)
    st.session_state.dp_loan_values.pop(loan_id, None)
    st.session_state.pop("dp_results", None)


# ── Loan input rows ──────────────────────────────────────────────────────────

st.subheader("Loans")

for loan_id in st.session_state.dp_loan_ids:
    values = st.session_state.dp_loan_values[loan_id]
    with st.container(border=True):
        c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 2, 2, 2, 1])
        values["name"] = c1.text_input(
            "Name", value=values["name"], key=f"dp_name_{loan_id}"
        )
        values["balance"] = c2.number_input(
            "Balance ($)",
            min_value=0.01,
            step=100.0,
            value=values["balance"],
            key=f"dp_balance_{loan_id}",
        )
        values["apr"] = c3.number_input(
            "APR (%)",
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            value=values["apr"],
            key=f"dp_apr_{loan_id}",
        )
        values["min"] = c4.number_input(
            "Min Payment ($)",
            min_value=0.01,
            step=10.0,
            value=values["min"],
            key=f"dp_min_{loan_id}",
        )
        values["comp"] = c5.selectbox(
            "Compounding",
            COMPOUNDING_OPTIONS,
            index=COMPOUNDING_OPTIONS.index(values["comp"]),
            key=f"dp_comp_{loan_id}",
        )
        if len(st.session_state.dp_loan_ids) > 1:
            c6.button(
                "✕",
                key=f"dp_remove_{loan_id}",
                on_click=remove_loan,
                args=(loan_id,),
                help="Remove this loan",
            )

        values["grace"] = st.checkbox(
            "Grace period (intro APR)",
            value=values["grace"],
            key=f"dp_grace_{loan_id}",
        )
        if values["grace"]:
            g1, g2 = st.columns(2)
            values["intro_apr"] = g1.number_input(
                "Intro APR (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                value=values["intro_apr"],
                key=f"dp_intro_apr_{loan_id}",
            )
            values["intro_end"] = g2.date_input(
                "Intro end date",
                value=values["intro_end"],
                key=f"dp_intro_end_{loan_id}",
            )

st.button("+ Add Loan", on_click=add_loan)

# ── Simulation settings ──────────────────────────────────────────────────────

st.subheader("Settings")

if "dp_start_date" not in st.session_state:
    st.session_state.dp_start_date: date = date.today()

start_date: date = st.date_input(  # type: ignore[assignment]
    "Simulation start date", value=st.session_state.dp_start_date
)
st.session_state.dp_start_date = start_date

sum_minimums = sum(
    float(st.session_state.dp_loan_values[lid]["min"])
    for lid in st.session_state.dp_loan_ids
)

ceiling_floor = sum_minimums + 1.0
stored_ceiling = st.session_state.get("dp_budget_ceiling", 0.0)
if stored_ceiling < ceiling_floor:
    stored_ceiling = max(sum_minimums * 2, sum_minimums + 500.0)

set_col, slider_col = st.columns([1, 3])
budget_ceiling = set_col.number_input(
    "Budget ceiling ($)",
    min_value=ceiling_floor,
    value=stored_ceiling,
    step=100.0,
)
st.session_state.dp_budget_ceiling = float(budget_ceiling)

stored_budget = float(st.session_state.get("dp_monthly_budget", sum_minimums))
stored_budget = min(max(stored_budget, sum_minimums), float(budget_ceiling))

monthly_budget = slider_col.slider(
    "Monthly budget ($)",
    min_value=sum_minimums,
    max_value=float(budget_ceiling),
    value=stored_budget,
    step=1.0,
    help="Drag to set total monthly payment across all loans",
)
st.session_state.dp_monthly_budget = float(monthly_budget)

# ── Calculate ────────────────────────────────────────────────────────────────

if st.button("Calculate", type="primary"):
    # A failed run must not leave the previous run's table and chart on screen.
    st.session_state.pop("dp_results", None)

    loans: list[Loan] = []
    build_errors: list[str] = []

    for loan_id in st.session_state.dp_loan_ids:
        values = st.session_state.dp_loan_values[loan_id]
        label = str(values["name"]).strip() or f"Loan {loan_id}"
        try:
            mode = (
                CompoundingMode.DAILY
                if values["comp"] == "Daily"
                else CompoundingMode.MONTHLY
            )
            has_grace = bool(values["grace"])
            intro_apr = Decimal(str(values["intro_apr"])) / 100 if has_grace else None
            intro_end = values["intro_end"] if has_grace else None
            loans.append(
                Loan(
                    name=str(values["name"]),
                    balance=Decimal(str(values["balance"])),
                    apr=Decimal(str(values["apr"])) / 100,
                    min_payment=Decimal(str(values["min"])),
                    compounding_mode=mode,
                    intro_apr=intro_apr,
                    intro_end_date=intro_end,
                )
            )
        except Exception as exc:
            build_errors.append(f"{label}: {exc}")

    if build_errors:
        for err in build_errors:
            st.error(err)
    else:
        try:
            budget_dec = Decimal(str(monthly_budget))
            sb = simulate_payoff(loans, budget_dec, "snowball", start_date)
            av = simulate_payoff(loans, budget_dec, "avalanche", start_date)
            st.session_state.dp_results = {"snowball": sb, "avalanche": av}
        except HorizonExceededError:
            needed = minimum_budget_to_clear(loans, start_date).to_integral_value(
                rounding=ROUND_CEILING
            )
            st.error(
                f"**Impossible at this budget.** At ${monthly_budget:,.2f} a month "
                "these loans are not paid off within ten years. A monthly budget of "
                f"**${needed:,}** would clear them within ten years."
            )
        except ValueError as exc:
            st.error(str(exc))

# ── Results ───────────────────────────────────────────────────────────────────

if "dp_results" in st.session_state:
    res = st.session_state.dp_results
    snowball_res = res["snowball"]
    avalanche_res = res["avalanche"]

    st.subheader("Comparison")

    def _summary_row(method_results: list, label: str) -> dict:  # type: ignore[type-arg]
        total_interest = sum(r.total_interest for r in method_results)
        payoff_date = max(r.payoff_date for r in method_results)
        months_count = len({s.month for r in method_results for s in r.snapshots})
        return {
            "Method": label,
            "Total Interest": f"${float(total_interest):,.2f}",
            "Months": months_count,
            "Payoff Date": payoff_date.strftime("%b %Y"),
        }

    st.dataframe(
        [
            _summary_row(snowball_res, "Snowball (lowest balance first)"),
            _summary_row(avalanche_res, "Avalanche (highest interest first)"),
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Remaining Debt Over Time")

    def _balance_series(method_results: list) -> tuple[list, list]:  # type: ignore[type-arg]
        bal: dict = defaultdict(Decimal)
        for r in method_results:
            for s in r.snapshots:
                bal[s.month] += s.remaining_balance
        months = sorted(bal.keys())
        return months, [float(bal[m]) for m in months]

    sb_x, sb_y = _balance_series(snowball_res)
    av_x, av_y = _balance_series(avalanche_res)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=sb_x, y=sb_y, name="Snowball (lowest balance first)", mode="lines")
    )
    fig.add_trace(
        go.Scatter(
            x=av_x, y=av_y, name="Avalanche (highest interest first)", mode="lines"
        )
    )
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Total Remaining Balance ($)",
        yaxis_tickprefix="$",
        yaxis_tickformat=",.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Detail")

    def _render_detail(method_results: list, label: str) -> None:  # type: ignore[type-arg]
        with st.expander(label):
            all_months = sorted({s.month for r in method_results for s in r.snapshots})
            snap_index = {
                (r.loan_name, s.month): s for r in method_results for s in r.snapshots
            }
            loan_names = [r.loan_name for r in method_results]
            table_rows = []
            for m in all_months:
                row: dict = {"Month": m.strftime("%b %Y")}
                for name in loan_names:
                    snap = snap_index.get((name, m))
                    row[name] = (
                        f"${float(snap.remaining_balance):,.2f}" if snap else "—"
                    )
                table_rows.append(row)
            st.dataframe(table_rows, use_container_width=True, hide_index=True)

    _render_detail(snowball_res, "Snowball (lowest balance first)")
    _render_detail(avalanche_res, "Avalanche (highest interest first)")
