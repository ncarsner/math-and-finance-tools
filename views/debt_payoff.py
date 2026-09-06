from collections import defaultdict
from datetime import date
from decimal import Decimal

import plotly.graph_objects as go
import streamlit as st

from math_finance_tools.debt_payoff import CompoundingMode, Loan, simulate_payoff

st.title("Debt Payoff Calculator")

# ── Session state initialisation ─────────────────────────────────────────────

if "dp_loan_ids" not in st.session_state:
    st.session_state.dp_loan_ids: list[int] = [0]
    st.session_state.dp_next_id: int = 1
    st.session_state["dp_name_0"] = "Loan 1"
    st.session_state["dp_balance_0"] = 5000.0
    st.session_state["dp_apr_0"] = 18.0
    st.session_state["dp_min_0"] = 100.0
    st.session_state["dp_comp_0"] = "Monthly"
    st.session_state["dp_grace_0"] = False
    st.session_state["dp_intro_apr_0"] = 0.0
    st.session_state["dp_intro_end_0"] = date.today()


def _loan_defaults(loan_id: int, n: int) -> None:
    st.session_state[f"dp_name_{loan_id}"] = f"Loan {n}"
    st.session_state[f"dp_balance_{loan_id}"] = 1000.0
    st.session_state[f"dp_apr_{loan_id}"] = 10.0
    st.session_state[f"dp_min_{loan_id}"] = 25.0
    st.session_state[f"dp_comp_{loan_id}"] = "Monthly"
    st.session_state[f"dp_grace_{loan_id}"] = False
    st.session_state[f"dp_intro_apr_{loan_id}"] = 0.0
    st.session_state[f"dp_intro_end_{loan_id}"] = date.today()


def add_loan() -> None:
    new_id: int = st.session_state.dp_next_id
    st.session_state.dp_next_id += 1
    _loan_defaults(new_id, len(st.session_state.dp_loan_ids) + 1)
    st.session_state.dp_loan_ids.append(new_id)


def remove_loan(loan_id: int) -> None:
    st.session_state.dp_loan_ids.remove(loan_id)
    for field in [
        "name",
        "balance",
        "apr",
        "min",
        "comp",
        "grace",
        "intro_apr",
        "intro_end",
    ]:
        st.session_state.pop(f"dp_{field}_{loan_id}", None)


# ── Loan input rows ──────────────────────────────────────────────────────────

st.subheader("Loans")

for loan_id in st.session_state.dp_loan_ids:
    with st.container(border=True):
        c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 2, 2, 2, 1])
        c1.text_input("Name", key=f"dp_name_{loan_id}")
        c2.number_input(
            "Balance ($)", min_value=0.01, step=100.0, key=f"dp_balance_{loan_id}"
        )
        c3.number_input(
            "APR (%)", min_value=0.0, max_value=100.0, step=0.1, key=f"dp_apr_{loan_id}"
        )
        c4.number_input(
            "Min Payment ($)", min_value=0.01, step=10.0, key=f"dp_min_{loan_id}"
        )
        c5.selectbox("Compounding", ["Monthly", "Daily"], key=f"dp_comp_{loan_id}")
        if len(st.session_state.dp_loan_ids) > 1:
            c6.button(
                "✕",
                key=f"dp_remove_{loan_id}",
                on_click=remove_loan,
                args=(loan_id,),
                help="Remove this loan",
            )

        if st.checkbox("Grace period (intro APR)", key=f"dp_grace_{loan_id}"):
            g1, g2 = st.columns(2)
            g1.number_input(
                "Intro APR (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                key=f"dp_intro_apr_{loan_id}",
            )
            g2.date_input("Intro end date", key=f"dp_intro_end_{loan_id}")

st.button("+ Add Loan", on_click=add_loan)

# ── Simulation settings ──────────────────────────────────────────────────────

st.subheader("Settings")

start_date: date = st.date_input("Simulation start date", value=date.today())  # type: ignore[assignment]

sum_minimums = sum(
    float(st.session_state.get(f"dp_min_{lid}", 0.0))
    for lid in st.session_state.dp_loan_ids
)

set_col, slider_col = st.columns([1, 3])
budget_ceiling = set_col.number_input(
    "Budget ceiling ($)",
    min_value=sum_minimums + 1.0,
    value=max(sum_minimums * 2, sum_minimums + 500.0),
    step=100.0,
)
monthly_budget = slider_col.slider(
    "Monthly budget ($)",
    min_value=sum_minimums,
    max_value=float(budget_ceiling),
    value=sum_minimums,
    step=1.0,
    help="Drag to set total monthly payment across all loans",
)

if monthly_budget < sum_minimums:
    st.error(
        f"Budget (${monthly_budget:,.2f}) is below the sum of minimum payments (${sum_minimums:,.2f})."
    )
    st.stop()

# ── Calculate ────────────────────────────────────────────────────────────────

if st.button("Calculate", type="primary"):
    loans: list[Loan] = []
    build_errors: list[str] = []

    for loan_id in st.session_state.dp_loan_ids:
        try:
            mode = (
                CompoundingMode.DAILY
                if st.session_state.get(f"dp_comp_{loan_id}") == "Daily"
                else CompoundingMode.MONTHLY
            )
            has_grace = bool(st.session_state.get(f"dp_grace_{loan_id}", False))
            intro_apr = (
                Decimal(str(st.session_state.get(f"dp_intro_apr_{loan_id}", 0.0))) / 100
                if has_grace
                else None
            )
            intro_end = (
                st.session_state.get(f"dp_intro_end_{loan_id}") if has_grace else None
            )
            loans.append(
                Loan(
                    name=str(
                        st.session_state.get(f"dp_name_{loan_id}", f"Loan {loan_id}")
                    ),
                    balance=Decimal(
                        str(st.session_state.get(f"dp_balance_{loan_id}", 0.0))
                    ),
                    apr=Decimal(str(st.session_state.get(f"dp_apr_{loan_id}", 0.0)))
                    / 100,
                    min_payment=Decimal(
                        str(st.session_state.get(f"dp_min_{loan_id}", 0.0))
                    ),
                    compounding_mode=mode,
                    intro_apr=intro_apr,
                    intro_end_date=intro_end,
                )
            )
        except Exception as exc:
            build_errors.append(f"Loan {loan_id}: {exc}")

    if build_errors:
        for err in build_errors:
            st.error(err)
    else:
        try:
            budget_dec = Decimal(str(monthly_budget))
            sb = simulate_payoff(loans, budget_dec, "snowball", start_date)
            av = simulate_payoff(loans, budget_dec, "avalanche", start_date)
            st.session_state.dp_results = {"snowball": sb, "avalanche": av}
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
