from collections import defaultdict
from datetime import date
from decimal import ROUND_CEILING, Decimal
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from math_finance_tools.debt_payoff import (
    AVALANCHE_METHODS,
    CompoundingMode,
    ExtraPaymentComparison,
    HorizonExceededError,
    Loan,
    StrategyVerdict,
    compare_extra_payment,
    compare_strategies,
    minimum_budget_to_clear,
)

st.title("Debt Payoff Calculator")

COMPOUNDING_OPTIONS = ["Monthly", "Daily"]

# Avalanche runs both orderings and keeps the cheaper one; the label says which,
# so the computed choice stays visible instead of becoming a hidden heuristic.
SNOWBALL_LABEL = "Snowball (lowest balance first)"
AVALANCHE_LABELS = {
    "static": "Avalanche (rate order)",
    "effective": "Avalanche (promotional-rate aware)",
}

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


def clear_results() -> None:
    """A changed input invalidates every stored run, not just the first."""
    st.session_state.pop("dp_results", None)
    st.session_state.pop("dp_extra", None)


def add_loan() -> None:
    new_id: int = st.session_state.dp_next_id
    st.session_state.dp_next_id += 1
    st.session_state.dp_loan_values[new_id] = _loan_defaults(
        len(st.session_state.dp_loan_ids) + 1
    )
    st.session_state.dp_loan_ids.append(new_id)
    clear_results()


def remove_loan(loan_id: int) -> None:
    st.session_state.dp_loan_ids.remove(loan_id)
    st.session_state.dp_loan_values.pop(loan_id, None)
    clear_results()


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

# An increment *between* two runs, never called extra: surplus is already the
# budget above the minimums cascaded *within* a run. At zero the comparison
# does not run at all, so it costs nothing to anyone not using it.
additional_budget = st.number_input(
    "Additional monthly payment ($)",
    min_value=0.0,
    value=float(st.session_state.get("dp_additional_budget", 0.0)),
    step=25.0,
    help="What a further amount each month would buy, on top of the budget above",
)
st.session_state.dp_additional_budget = float(additional_budget)

# ── Calculate ────────────────────────────────────────────────────────────────

if st.button("Calculate", type="primary"):
    # A failed run must not leave the previous run's table and chart on screen.
    clear_results()

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
            verdict_result = compare_strategies(loans, budget_dec, start_date)
            extra_result: dict[str, Any] | None = None
            if additional_budget > 0:
                additional_dec = Decimal(str(additional_budget))
                avalanche_method = AVALANCHE_METHODS[verdict_result.avalanche_ordering]
                # Each strategy is compared against itself at the higher budget,
                # so the increment is the only thing that moves.
                extra_result = {
                    "additional": float(additional_budget),
                    "snowball": compare_extra_payment(
                        loans, budget_dec, additional_dec, "snowball", start_date
                    ),
                    "avalanche": compare_extra_payment(
                        loans, budget_dec, additional_dec, avalanche_method, start_date
                    ),
                }
            # Stored last: a failure in any run above leaves nothing on screen.
            st.session_state.dp_results = verdict_result
            if extra_result is not None:
                st.session_state.dp_extra = extra_result
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
    verdict: StrategyVerdict = st.session_state.dp_results
    snowball_res = list(verdict.snowball)
    avalanche_res = list(verdict.avalanche.results)
    avalanche_label = AVALANCHE_LABELS[verdict.avalanche_ordering]

    # ── Verdict ──────────────────────────────────────────────────────────────
    #
    # A winner is named at every margin: a small win is reported as small,
    # never softened into a tie.

    def _months(n: int) -> str:
        return f"{n} month" if n == 1 else f"{n} months"

    winner_label = SNOWBALL_LABEL if verdict.winner == "snowball" else avalanche_label
    if verdict.months_delta > 0:
        timing = f"and finishes {_months(verdict.months_delta)} sooner"
    elif verdict.months_delta < 0:
        timing = f"but takes {_months(-verdict.months_delta)} longer"
    else:
        timing = "and finishes in the same month"

    st.subheader("Verdict")
    if verdict.interest_delta > 0:
        st.success(
            f"**{winner_label}** saves **${verdict.interest_delta:,.2f}** "
            f"in interest {timing}."
        )
    else:
        sf = verdict.snowball_first_clear_months
        af = verdict.avalanche_first_clear_months
        if sf < af:
            reason = (
                "so it goes to snowball, which clears its first loan sooner: "
                f"month {sf} against month {af}."
            )
        elif sf == af:
            reason = (
                "and both clear their first loan in the same month, so the tie "
                "goes to snowball."
            )
        else:
            reason = (
                "so the tie goes to snowball, though avalanche clears its first "
                f"loan sooner: month {af} against month {sf}."
            )
        st.success(
            f"**{winner_label}** — both strategies cost "
            f"${verdict.winner_total_interest:,.2f} in interest, {reason}"
        )

    st.subheader("Comparison")

    def _summary_row(
        method_results: list,  # type: ignore[type-arg]
        label: str,
        first_clear_months: int,
    ) -> dict:  # type: ignore[type-arg]
        total_interest = sum(r.total_interest for r in method_results)
        payoff_date = max(r.payoff_date for r in method_results)
        months_count = len({s.month for r in method_results for s in r.snapshots})
        return {
            "Method": label,
            "Total Interest": f"${float(total_interest):,.2f}",
            "First loan cleared": f"Month {first_clear_months}",
            "Months": months_count,
            "Payoff Date": payoff_date.strftime("%b %Y"),
        }

    st.dataframe(
        [
            _summary_row(
                snowball_res, SNOWBALL_LABEL, verdict.snowball_first_clear_months
            ),
            _summary_row(
                avalanche_res, avalanche_label, verdict.avalanche_first_clear_months
            ),
        ],
        use_container_width=True,
        hide_index=True,
    )

    extra = st.session_state.get("dp_extra")

    def _dollars(amount: float) -> str:
        """Whole dollars read cleaner; cents show only when there are any."""
        return f"${amount:,.0f}" if amount.is_integer() else f"${amount:,.2f}"

    if extra is not None:
        additional_amount = float(extra["additional"])
        st.subheader(f"Adding {_dollars(additional_amount)} a Month")

        def _savings_row(comparison: ExtraPaymentComparison, label: str) -> dict:  # type: ignore[type-arg]
            return {
                "Method": label,
                "Months saved": comparison.months_saved,
                "Interest saved": f"${float(comparison.interest_saved):,.2f}",
                "Payoff Date": comparison.accelerated_payoff_date.strftime("%b %Y"),
                "Was": comparison.baseline_payoff_date.strftime("%b %Y"),
            }

        st.dataframe(
            [
                _savings_row(extra["snowball"], SNOWBALL_LABEL),
                _savings_row(extra["avalanche"], avalanche_label),
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
    fig.add_trace(go.Scatter(x=sb_x, y=sb_y, name=SNOWBALL_LABEL, mode="lines"))
    fig.add_trace(go.Scatter(x=av_x, y=av_y, name=avalanche_label, mode="lines"))

    if extra is not None:
        # Four traces with the comparison active: each strategy against itself.
        suffix = f" + {_dollars(float(extra['additional']))}"
        for key, label in (
            ("snowball", SNOWBALL_LABEL),
            ("avalanche", avalanche_label),
        ):
            acc_x, acc_y = _balance_series(list(extra[key].accelerated))
            fig.add_trace(
                go.Scatter(
                    x=acc_x,
                    y=acc_y,
                    name=label + suffix,
                    mode="lines",
                    line=dict(dash="dash"),
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

    _render_detail(snowball_res, SNOWBALL_LABEL)
    _render_detail(avalanche_res, avalanche_label)
