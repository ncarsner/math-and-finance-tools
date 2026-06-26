import streamlit as st

st.set_page_config(page_title="Math & Finance Tools", layout="wide")

pg = st.navigation(
    [
        st.Page("pages/0_Home.py", title="Home", default=True),
        st.Page("pages/1_Debt_Payoff.py", title="Debt Payoff Calculator"),
        st.Page("pages/2_Composite_Rate.py", title="Composite Rate Calculator"),
    ]
)
pg.run()
