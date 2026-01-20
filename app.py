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

# --- PŘIHLÁŠENÍ ---
st.sidebar.header("👤 Přihlášení hráče")
user_name = st.sidebar.text_input("Tvoje přezdívka (např. Štamgast_Franta)")
user_pin = st.sidebar.text_input("Tvůj PIN (4 čísla)", type="password")

if user_name and user_pin:
    st.header("📝 Podat tip")
    
    # Filtrace zápasů, které jsou "budoucí"
    future_matches = df[df['status'] == 'budoucí']
    
    if not future_matches.empty:
        match_to_tip = st.selectbox("Vyber zápas:", future_matches['team_a'] + " vs " + future_matches['team_b'])
        
        col1, col2 = st.columns(2)
        with col1:
            score_a = st.number_input("Góly Domácí", min_value=0, step=1, key="a")
        with col2:
            score_b = st.number_input("Góly Hosté", min_value=0, step=1, key="b")
            
        if st.button("Odeslat tip"):
            # Zde vytvoříme řádek pro uložení
            new_bet = {
                "user": user_name,
                "match": match_to_tip,
                "tip": f"{score_a}:{score_b}",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.balloons()
            st.success(f"Tip na zápas {match_to_tip} uložen! ({score_a}:{score_b})")
            # SEM vložíme kód pro zápis do Google Sheets
    else:
        st.info("Momentálně nejsou k dispozici žádné zápasy k tipování.")

if user_name and user_pin:
    st.sidebar.success(f"Přihlášen jako: {user_name}")
else:
    st.sidebar.warning("Pro tipování se prosím identifikuj vlevo.")
