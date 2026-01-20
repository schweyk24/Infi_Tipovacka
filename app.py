import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("🏒 Barová Tipovačka")

# Očištěná URL
URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Zkusíme načíst list 'Matches'
    data = conn.read(spreadsheet=URL, worksheet="Matches")
    st.success("Připojeno!")
    st.dataframe(data)
except Exception as e:
    st.error(f"Chyba: {e}")
    st.info("Zkuste v Google Sheets přejmenovat list na 'Matches' nebo v kódu změnit worksheet na 'List1'")
