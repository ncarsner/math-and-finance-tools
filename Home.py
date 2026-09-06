import streamlit as st

st.set_page_config(page_title="Math & Finance Tools", layout="wide")

pg = st.navigation(
    [
        st.Page("views/home.py", title="Home", default=True),
        st.Page("views/debt_payoff.py", title="Debt Payoff Calculator"),
        st.Page("views/composite_rate.py", title="Composite Rate Calculator"),
    ]
)
pg.run()
