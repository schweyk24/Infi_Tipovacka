import streamlit as st
import pandas as pd

st.set_page_config(page_title="Hokejová Tipovačka", layout="centered")
st.title("🏒 Barová Tipovačka")

# Toto je váš odkaz upravený tak, aby z něj šlo přímo číst (export jako CSV)
# To ID je z vašeho odkazu: 1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU
SHEET_ID = "1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU"
SHEET_NAME = "Matches"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

st.info("Pokouším se načíst data z Google Sheets...")

try:
    # Přímé načtení přes Pandas - nejstabilnější metoda pro čtení veřejných tabulek
    df = pd.read_csv(URL)
    
    if len(df) > 0:
        st.success("✅ Spojení navázáno! Tabulka načtena.")
        st.write("Aktuální zápasy v systému:")
        st.dataframe(df)
    else:
        st.warning("Tabulka byla nalezena, ale list 'Matches' neobsahuje žádná data pod hlavičkou.")

except Exception as e:
    st.error(f"❌ Chyba: {e}")
    st.write("Zkuste v Google Sheets: Soubor -> Sdílet -> Publikovat na web")
