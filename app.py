import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Tipovačka Test")

# Odkaz na tabulku (zkrácený)
URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRsYyYfKaVPBHe6FzwS_L6HgG-uN8YIHpqfkn7eUQ7HqpN4n43Ufpx_ZQ_Zl7re2oWTwl9Zeuuhgtbt/pubhtml"

# Inicializace připojení
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🏒 Připojení k tabulce")

try:
    # ttl=0 zajistí, že se data nebudou cachovat a načtou se vždy čerstvá
    df = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0)
    
    if df.empty:
        st.warning("Tabulka je připojená, ale vypadá to, že v listu 'Matches' nejsou žádná data (jen hlavičky?).")
    else:
        st.success("Data byla úspěšně načtena!")
        st.write("Náhled dat z listu Matches:")
        st.dataframe(df)

except Exception as e:
    st.error(f"Chyba: {e}")
    st.info("Zkuste v Streamlit Secrets (v nastavení na webu) zkontrolovat, zda máte správně zadanou URL.")
