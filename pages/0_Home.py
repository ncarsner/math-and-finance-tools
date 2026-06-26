import streamlit as st

st.title("Math & Finance Tools")
st.write(
    "A suite of personal finance calculators to help you understand "
    "the math behind debt repayment and interest costs."
)

st.subheader("Debt Payoff Calculator")
st.write(
    "Compare the **Snowball** (lowest balance first) and **Avalanche** "
    "(highest interest first) repayment strategies side by side. "
    "Enter your loans, set a monthly budget, and see the difference in "
    "total interest paid and projected payoff date."
)
st.write("Select **Debt Payoff Calculator** in the sidebar to get started.")

st.subheader("Composite Rate Calculator")
st.write(
    "See your blended interest rate across all accounts. "
    "Accounts above the composite rate are your highest-priority payoff "
    "targets; accounts at or below are relatively cheaper debt."
)
st.write("Select **Composite Rate Calculator** in the sidebar to get started.")
