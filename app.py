import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Hokejová Tipovačka", layout="centered")

# --- PROPOJENÍ S GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Načteme zápasy
df_matches = conn.read(worksheet="Matches", ttl=0)

st.title("🏒 Barová Tipovačka 2026")

# --- IDENTIFIKACE ---
st.sidebar.header("Přihlášení")
user = st.sidebar.text_input("Přezdívka (např. Jirka)")
pin = st.sidebar.text_input("PIN (4 čísla)", type="password")

if user and pin:
    st.sidebar.success(f"Přihlášen: {user}")
    
    # --- FORMULÁŘ PRO TIPOVÁNÍ ---
    st.header("Zadej svůj tip")
    
    # Filtrujeme pouze zápasy se statusem 'budoucí'
    open_matches = df_matches[df_matches['status'] == 'budoucí']
    
    if not open_matches.empty:
        # Vytvoření seznamu zápasů pro výběr
        match_list = open_matches['team_a'] + " vs " + open_matches['team_b']
        selected_match_text = st.selectbox("Vyber zápas:", match_list)
        
        # Získání ID zápasu
        idx = match_list[match_list == selected_match_text].index[0]
        m_id = open_matches.loc[idx, 'match_id']
        t_a = open_matches.loc[idx, 'team_a']
        t_b = open_matches.loc[idx, 'team_b']
        
        col1, col2 = st.columns(2)
        with col1:
            score_a = st.number_input(f"Góly {t_a}", min_value=0, step=1)
        with col2:
            score_b = st.number_input(f"Góly {t_b}", min_value=0, step=1)
            
        if st.button("🚀 Odeslat tip"):
            # Vytvoření nového řádku
            new_bet = pd.DataFrame([{
                "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "user_name": user,
                "match_id": str(m_id),
                "tip_a": int(score_a),
                "tip_b": int(score_b),
                "points_earned": 0
            }])
            
            try:
                # Načtení stávajících tipů z listu Bets
                existing_bets = conn.read(worksheet="Bets", ttl=0)
                # Spojení starých a nových dat
                updated_bets = pd.concat([existing_bets, new_bet], ignore_index=True)
                # Zápis zpět do listu Bets
                conn.update(worksheet="Bets", data=updated_bets)
                
                st.balloons()
                st.success(f"Tip na {t_a} {score_a}:{score_b} {t_b} byl uložen do systému!")
            except Exception as e:
                st.error(f"Chyba při zápisu do tabulky: {e}")
    else:
        st.info("Aktuálně nejsou žádné otevřené zápasy k tipování.")
else:
    st.info("Pro tipování se prosím přihlas v postranním panelu vlevo.")

# Pro kontrolu (můžete smazat, až to bude fungovat)
if st.checkbox("Zobrazit list Bets (pro kontrolu)"):
    st.write(conn.read(worksheet="Bets", ttl=0))
