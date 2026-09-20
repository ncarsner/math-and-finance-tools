import streamlit as st

st.title("Math & Finance Tools")
st.write(
    "A suite of personal finance calculators to help you understand "
    "the math behind debt repayment and interest costs."
)

st.subheader("Debt Payoff Calculator")
st.write(
    "Compare the **Snowball** (lowest balance first) and **Avalanche** "
    "(rate-driven) repayment strategies side by side. Enter your loans, set a "
    "monthly budget, and the page names the winning strategy, the interest it "
    "saves and the months it takes off — along with the total interest, payoff "
    "date and the month your first loan clears for each. Add an amount to your "
    "monthly budget to see what paying more would buy."
)
st.write("Select **Debt Payoff Calculator** in the sidebar to get started.")

st.subheader("Composite Rate Calculator")
st.write(
    "See your blended interest rate across all accounts. "
    "Accounts above the composite rate are your highest-priority payoff "
    "targets; accounts at or below are relatively cheaper debt."
)
st.write("Select **Composite Rate Calculator** in the sidebar to get started.")

st.subheader("Debt vs. Invest")
st.write(
    "Decide whether a spare dollar is worth more against your debt or in the "
    "market. Your debt rate is compared against an expected return after tax — "
    "taken whole in a 401(k) or IRA, reduced by capital gains tax in a "
    "brokerage — and the page names the side the spread favors. Your composite "
    "rate carries over as the debt rate if you have calculated one."
)
st.write("Select **Debt vs. Invest** in the sidebar to get started.")
