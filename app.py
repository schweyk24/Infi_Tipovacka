import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Nastavení stránky
st.set_page_config(page_title="Barová Tipovačka", layout="centered")

st.title("🏒 Tipovačka: Infinity Bar")

# --- PROPOJENÍ S GOOGLE SHEETS ---
# URL vaší tabulky (vložte ji mezi uvozovky níže)
URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(spreadsheet=URL, worksheet="Matches")
    
    st.success("Připojeno k databázi!")
    
    # Zobrazení aktuálních zápasů z tabulky
    st.subheader("Aktuální rozpis zápasů")
    st.dataframe(data)

except Exception as e:
    st.error(f"Chyba při připojení: {e}")
    st.info("Tip: Zkontrolujte, zda je list v tabulce pojmenován přesně 'Matches'.")

# --- SEKCE PRO TIPOVÁNÍ ---
with st.expander("Podat tip na zápas"):
    st.write("Tady budeme brzy zadávat skóre!")
