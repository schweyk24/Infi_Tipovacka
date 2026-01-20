import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="Hokejová Tipovačka 2026", layout="centered")

# --- PROPOJENÍ A DATA ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Matches", ttl=60)
    df_b = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Bets", ttl=60)
    df_u = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Users", ttl=60)
    
    df_m['match_id'] = df_m['match_id'].astype(str)
    if not df_b.empty:
        df_b['match_id'] = df_b['match_id'].astype(str)
    return conn, df_m, df_b, df_u

try:
    conn, df_matches, df_bets, df_users = load_data()
except Exception as e:
    st.error(f"Chyba připojení k databázi: {e}")
    st.stop()

if 'user' not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR: Přihlášení a Registrace ---
st.sidebar.title("🏒 Tipovačka Bar")

if st.session_state.user:
    st.sidebar.success(f"Přihlášen: **{st.session_state.user}**")
    if st.sidebar.button("Odhlásit se"):
        st.session_state.user = None
        st.rerun()
else:
    u_in = st.sidebar.text_input("Tvoje přezdívka")
    p_in = st.sidebar.text_input("PIN (4 čísla)", type="password")
    if st.sidebar.button("Vstoupit do hry"):
        if u_in and len(p_in) == 4:
            if u_in not in df_users['user_name'].values:
                new_u = pd.DataFrame([{"user_name": u_in, "pin": p_in, "total_points": 0}])
                updated_u = pd.concat([df_users, new_u], ignore_index=True)
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Users", data=updated_u)
                st.cache_data.clear()
            st.session_state.user = u_in
            st.rerun()
        else:
            st.sidebar.warning("Zadej jméno a 4místný PIN.")

# --- ADMIN SEKCE ---
if st.sidebar.checkbox("Režim Barman"):
    pwd = st.sidebar.text_input("Admin heslo", type="password")
    if pwd == "hokej2026":
        st.header("⚙️ Administrace")
        to_score = df_matches[df_matches['status'] != 'ukončeno']
        if not to_score.empty:
            m_select = st.selectbox("Zápas:", to_score['team_a'] + " vs " + to_score['team_b'])
            idx = to_score[to_score['team_a'] + " vs " + to_score['team_b'] == m_select].index[0]
            m_id = str(to_score.loc[idx, 'match_id'])
            
            c1, c2 = st.columns(2)
            res_a = c1.number_input(f"Skóre {to_score.loc[idx, 'team_a']}", min_value=0)
            res_b = c2.number_input(f"Skóre {to_score.loc[idx, 'team_b']}", min_value=0)
            
            if st.button("✅ Vyhodnotit"):
                def calc_pts(ta, tb, ra, rb):
                    if ta == ra and tb == rb: return 5
                    if (ra-rb) == (ta-tb): return 3
                    if (ra>rb and ta>tb) or (ra<rb and ta<tb): return 2
                    return 0

                if not df_bets.empty:
                    df_bets['points_earned'] = df_bets.apply(
                        lambda x: calc_pts(x['tip_a'], x['tip_b'], res_a, res_b) if x['match_id'] == m_id else x['points_earned'], axis=1
                    )
                
                df_matches.loc[df_matches['match_id'] == m_id, ['result_a', 'result_b', 'status']] = [res_a, res_b, 'ukončeno']
                
                # Přepočet Users
                new_totals = df_bets.groupby('user_name')['points_earned'].sum().reset_index()
                df_users = df_users.drop(columns=['total_points']).merge(new_totals, on='user_name', how='left').fillna(0)
                df_users.rename(columns={'points_earned': 'total_points'}, inplace=True)

                conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Bets", data=df_bets)
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Matches", data=df_matches)
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Users", data=df_users)
                
                st.cache_data.clear()
                st.rerun()
        st.stop()

# --- HRÁČSKÁ SEKCE ---
if st.session_state.user:
    st.title(f"Ahoj {st.session_state.user}!")
    t1, t2, t3 = st.tabs(["📝 Tipovat", "🏆 Pořadí", "📅 Výsledky"])

    with t1:
        st.subheader("Otevřené zápasy")
        open_m = df_matches[df_matches['status'] == 'budoucí']
        if not open_m.empty:
            m_opt = open_m['team_a'] + " vs " + open_m['team_b']
            sel_m = st.
