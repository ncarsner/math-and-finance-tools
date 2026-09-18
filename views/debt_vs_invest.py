from decimal import Decimal

import streamlit as st

from math_finance_tools.debt_vs_invest import (
    AccountType,
    Recommendation,
    compare_debt_vs_invest,
)

st.title("Debt vs. Invest")
st.write(
    "Whether a spare dollar is worth more against the debt or in the market, "
    "compared as rates: what the debt costs against what an investment is "
    "expected to return once tax is taken out."
)

# The Composite Rate page writes its result to this plain key. Streamlit
# garbage-collects widget-associated keys when a page stops rendering but never
# plain ones, so the handoff survives navigation. The coupling is one
# directional: this page reads it and never writes it.
COMPOSITE_APR_KEY = "shared_composite_apr"
DEFAULT_DEBT_APR = 18.0
DEFAULT_EXPECTED_RETURN = 7.0
DEFAULT_CAPITAL_GAINS_RATE = 15.0

ACCOUNT_TYPES = {
    "Tax-advantaged (401(k), IRA, HSA)": AccountType.TAX_ADVANTAGED,
    "Taxable brokerage": AccountType.TAXABLE,
}

# ── Inputs ───────────────────────────────────────────────────────────────────
#
# Reactive, like Composite Rate: the whole calculation is a handful of
# arithmetic operations, so there is nothing for a Calculate button to defer.

rate_col, return_col = st.columns(2)

debt_apr_pct = rate_col.number_input(
    "Debt APR (%)",
    min_value=0.0,
    max_value=100.0,
    step=0.1,
    value=float(st.session_state.get(COMPOSITE_APR_KEY, DEFAULT_DEBT_APR)),
    help=(
        "Enter the rate after any tax deduction you actually claim. "
        "Deductible interest is not modelled here."
    ),
)
expected_return_pct = return_col.number_input(
    "Expected annual return (%)",
    min_value=0.0,
    max_value=100.0,
    step=0.1,
    value=DEFAULT_EXPECTED_RETURN,
    help="Nominal, before tax. Inflation cancels in the comparison.",
)

account_type_label = st.radio("Account type", list(ACCOUNT_TYPES), horizontal=True)
account_type = ACCOUNT_TYPES[str(account_type_label)]

# Only a taxable account suffers annual drag, so the field appears only there.
capital_gains_pct = DEFAULT_CAPITAL_GAINS_RATE
if account_type is AccountType.TAXABLE:
    capital_gains_pct = st.number_input(
        "Capital gains rate (%)",
        min_value=0.0,
        max_value=99.9,
        step=0.5,
        value=DEFAULT_CAPITAL_GAINS_RATE,
    )

result = compare_debt_vs_invest(
    Decimal(str(debt_apr_pct)) / 100,
    Decimal(str(expected_return_pct)) / 100,
    account_type,
    Decimal(str(capital_gains_pct)) / 100,
)

# ── Result ───────────────────────────────────────────────────────────────────

spread_points = float(result.spread) * 100
after_tax_pct = float(result.after_tax_return) * 100

st.subheader("Recommendation")

if result.recommendation is Recommendation.PAY_DEBT:
    st.success(
        f"**Pay down the debt.** It costs {debt_apr_pct:.2f}% against an "
        f"after-tax return of {after_tax_pct:.2f}% — paying it off is a "
        f"guaranteed {-spread_points:.2f} points better."
    )
elif result.recommendation is Recommendation.INVEST:
    st.success(
        f"**Invest.** An after-tax return of {after_tax_pct:.2f}% beats "
        f"{debt_apr_pct:.2f}% debt by {spread_points:.2f} points — though the "
        "return is expected and the debt rate is certain."
    )
else:
    st.success(
        f"**Either.** Both sides come to {after_tax_pct:.2f}%, so the money is "
        "worth the same in each and the choice is yours to make on other grounds."
    )

m1, m2, m3 = st.columns(3)
m1.metric("Spread", f"{spread_points:+.2f} pts")
m2.metric("After-tax return", f"{after_tax_pct:.2f}%")
m3.metric("Debt APR", f"{debt_apr_pct:.2f}%")

st.caption(
    "Rates, not trajectories: no contribution schedule, no employer match, and "
    "no market path. Both sides are nominal, so inflation cancels between them."
)
