from decimal import Decimal

import plotly.graph_objects as go
import streamlit as st

from math_finance_tools.composite_rate import Account, calculate_composite_rate

st.title("Composite Rate Calculator")

# ── Session state initialisation ─────────────────────────────────────────────

if "cr_account_ids" not in st.session_state:
    st.session_state.cr_account_ids: list[int] = [0, 1]
    st.session_state.cr_next_id: int = 2
    st.session_state["cr_label_0"] = "Account 1"
    st.session_state["cr_balance_0"] = 5000.0
    st.session_state["cr_apr_0"] = 18.0
    st.session_state["cr_label_1"] = "Account 2"
    st.session_state["cr_balance_1"] = 3000.0
    st.session_state["cr_apr_1"] = 12.0


def _account_defaults(account_id: int, n: int) -> None:
    st.session_state[f"cr_label_{account_id}"] = f"Account {n}"
    st.session_state[f"cr_balance_{account_id}"] = 1000.0
    st.session_state[f"cr_apr_{account_id}"] = 10.0


def add_account() -> None:
    new_id: int = st.session_state.cr_next_id
    st.session_state.cr_next_id += 1
    _account_defaults(new_id, len(st.session_state.cr_account_ids) + 1)
    st.session_state.cr_account_ids.append(new_id)


def remove_account(account_id: int) -> None:
    st.session_state.cr_account_ids.remove(account_id)
    for field in ["label", "balance", "apr"]:
        st.session_state.pop(f"cr_{field}_{account_id}", None)


# ── Account input rows ───────────────────────────────────────────────────────

st.subheader("Accounts")

for account_id in st.session_state.cr_account_ids:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.text_input("Label", key=f"cr_label_{account_id}")
        c2.number_input(
            "Balance ($)", min_value=0.0, step=100.0, key=f"cr_balance_{account_id}"
        )
        c3.number_input(
            "APR (%)",
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            key=f"cr_apr_{account_id}",
        )
        if len(st.session_state.cr_account_ids) > 1:
            c4.button(
                "✕",
                key=f"cr_remove_{account_id}",
                on_click=remove_account,
                args=(account_id,),
                help="Remove this account",
            )

st.button("+ Add Account", on_click=add_account)

# ── Build accounts and compute ───────────────────────────────────────────────

accounts = [
    Account(
        label=str(st.session_state.get(f"cr_label_{aid}", f"Account {aid}")),
        balance=Decimal(str(st.session_state.get(f"cr_balance_{aid}", 0.0))),
        apr=Decimal(str(st.session_state.get(f"cr_apr_{aid}", 0.0))) / 100,
    )
    for aid in st.session_state.cr_account_ids
]

result = calculate_composite_rate(accounts)

# ── Metrics ───────────────────────────────────────────────────────────────────

st.subheader("Results")

m1, m2 = st.columns(2)
m1.metric(
    "Composite APR",
    f"{float(result.composite_apr) * 100:.4f}%",
)
m2.metric(
    "Monthly Interest Cost",
    f"${float(result.monthly_interest_cost):,.2f}",
)

# ── Per-account table ─────────────────────────────────────────────────────────

st.subheader("Account Breakdown")

table_rows = [
    {
        "Account": bd.label,
        "Balance": f"${float(bd.balance):,.2f}",
        "APR": f"{float(bd.apr) * 100:.2f}%",
        "Monthly Interest": f"${float(bd.monthly_interest):,.2f}",
        "% of Total Interest": f"{float(bd.interest_share) * 100:.1f}%",
    }
    for bd in result.per_account_breakdown
]
st.dataframe(table_rows, use_container_width=True, hide_index=True)

# ── Plotly scatter chart ──────────────────────────────────────────────────────

st.subheader("Rate vs. Balance")

composite_float = float(result.composite_apr) * 100

above = [
    bd for bd in result.per_account_breakdown if float(bd.apr) * 100 > composite_float
]
below = [
    bd for bd in result.per_account_breakdown if float(bd.apr) * 100 <= composite_float
]

fig = go.Figure()

if above:
    fig.add_trace(
        go.Scatter(
            x=[float(bd.apr) * 100 for bd in above],
            y=[float(bd.balance) for bd in above],
            mode="markers+text",
            name="Above composite",
            marker=dict(color="red", size=12),
            text=[bd.label for bd in above],
            textposition="top center",
        )
    )

if below:
    fig.add_trace(
        go.Scatter(
            x=[float(bd.apr) * 100 for bd in below],
            y=[float(bd.balance) for bd in below],
            mode="markers+text",
            name="At or below composite",
            marker=dict(color="green", size=12),
            text=[bd.label for bd in below],
            textposition="top center",
        )
    )

fig.add_vline(
    x=composite_float,
    line_dash="dash",
    line_color="gray",
    annotation_text=f"Composite {composite_float:.2f}%",
    annotation_position="top right",
)

fig.update_layout(
    xaxis_title="APR (%)",
    yaxis_title="Balance ($)",
    yaxis_tickprefix="$",
    yaxis_tickformat=",.0f",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)

st.plotly_chart(fig, use_container_width=True)
