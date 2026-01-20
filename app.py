import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="Hokejová Tipovačka 2026", layout="centered")

# --- PROPOJENÍ A DATA ---
# ID vaší tabulky z URL
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_matches = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Matches", ttl=0)
    df_bets = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Bets", ttl=0)
    
    # Sjednocení ID na text pro spolehlivé porovnávání
    df_matches['match_id'] = df_matches['match_id'].astype(str)
    if not df_bets.empty:
        df_bets['match_id'] = df_bets['match_id'].astype(str)
except Exception as e:
    st.error(f"Chyba připojení k databázi: {e}")
    st.stop()

# --- STAV PŘIHLÁŠENÍ (Session State) ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR (Menu) ---
st.sidebar.title("🏒 Tipovačka Bar")

if st.session_state.user:
    st.sidebar.success(f"Přihlášen: **{st.session_state.user}**")
    if st.sidebar.button("Odhlásit se"):
        st.session_state.user = None
        st.rerun()
else:
    user_in = st.sidebar.text_input("Tvoje přezdívka")
    pin_in = st.sidebar.text_input("PIN (4 čísla)", type="password")
    if st.sidebar.button("Vstoupit do hry"):
        if user_in and len(pin_in) == 4:
            st.session_state.user = user_in
            st.rerun()
        else:
            st.sidebar.warning("Zadej jméno a 4místný PIN.")

# --- ADMIN SEKCE ---
admin_mode = st.sidebar.checkbox("Režim Barman")
if admin_mode:
    pwd = st.sidebar.text_input("Admin heslo", type="password")
    if pwd == "hokej2026":
        st.header("⚙️ Administrace výsledků")
        
        # Výběr neukončeného zápasu
        to_score = df_matches[df_matches['status'] != 'ukončeno']
        if not to_score.empty:
            m_select = st.selectbox("Vyber zápas k vyhodnocení:", to_score['team_a'] + " vs " + to_score['team_b'])
            m_idx = to_score[to_score['team_a'] + " vs " + to_score['team_b'] == m_select].index[0]
            m_id = str(to_score.loc[m_idx, 'match_id'])
            
            c1, c2 = st.columns(2)
            res_a = c1.number_input(f"Skóre {to_score.loc[m_idx, 'team_a']}", min_value=0, step=1)
            res_b = c2.number_input(f"Skóre {to_score.loc[m_idx, 'team_b']}", min_value=0, step=1)
