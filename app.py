import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Hokejová Tipovačka 2026", layout="centered")

# --- CSS PRO GRAFIKU ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
    }
    .stExpander { border: 1px solid #31333f; border-radius: 10px; margin-bottom: 10px; }
    h1, h2, h3 { color: #f0f2f6 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1c24;
        border-radius: 5px;
        color: white;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=5) # Nízké TTL pro rychlou aktualizaci
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=5)
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=5)
    
    # Čištění dat Matches
    df_m['match_id'] = df_m['match_id'].astype(str)
    
    # Robustní zpracování času (spojení date a time pokud start_time chybí)
    if 'start_time' not in df_m.columns:
        df_m['start_time'] = df_m['date'].astype(str) + ' ' + df_m['time'].astype(str)
    
    df_m['start_time'] = pd.to_datetime(df_m['start_time'], dayfirst=True, errors='coerce')
    df_m = df_m.sort_values(by='start_time')
    
    # Sjednocení statusu na malá písmena bez mezer
    df_m['status'] = df_m['status'].astype(str).str.strip().str.lower()
    
    if not df_b.empty:
        df_b['match_id'] = df_b['match_id'].astype(str)
    
    return conn, df_m, df_b, df_u

try:
    conn, df_matches, df_bets, df_users = load_data()
except Exception as e:
    st.error(f"Chyba databáze: {e}")
    st.stop()

if 'user' not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR (PŘIHLÁŠENÍ) ---
with st.sidebar:
    st.title("🏒 Barová Tipovačka")
    if st.session_state.user:
        st.success(f"U stolu: **{st.session_state.user}**")
        u_pts = df_users[df_users['user_name'] == st.session_state.user]['total_points'].values
        pts = int(u_pts[0]) if len(u_pts) > 0 else 0
        st.metric("Tvoje body", pts)
        if st.button("Odhlásit se"):
            st.session_state.user = None
            st.rerun()
    else:
        u_in = st.text_input("Přezdívka")
        p_in = st.text_input("PIN (4 čísla)", type="password")
        if st.button("Vstoupit do hry"):
            if u_in and len(p_in) == 4:
                if u_in not in df_users['user_name'].values:
                    new_u = pd.DataFrame([{"user_name": u_in, "pin": p_in, "total_points": 0}])
                    up_u = pd.concat([df_users, new_u], ignore_index=True)
                    conn.update(spreadsheet=URL, worksheet="Users", data=up_u)
                    st.cache_data.clear()
                st.session_state.user = u_in
                st.rerun()

# --- ADMIN SEKCE (BARMAN) ---
if st.sidebar.checkbox("🔒 Režim Barman"):
    pwd = st.sidebar.text_input("Heslo", type="password")
    if pwd == "hokej2026":
        st.header("⚙️ Vyhodnocení zápasů")
        # Barman vidí vše kromě ukončených
        to_score = df_matches[df_matches['status'] != 'ukončeno'].copy()
        if not to_score.empty:
            to_score['date_only'] = to_score['start_time'].dt.strftime('%d.%m.%Y')
            for d in to_score['date_only'].unique():
                with st.expander(f"📅 Vyhodnotit: {d}", expanded=True):
                    day_m = to_score[to_score['date_only'] == d]
                    for _, m in day_m.iterrows():
                        mid = str(m['match_id'])
                        st.write(f"**{m['team_a']} vs {m['team_b']}**")
                        c1, c2, c3 = st.columns([1,1,1])
                        res_a = c1.number_input(f"{m['team_a']}", 0, 20, 0, key=f"a_{mid}")
                        res_b = c2.number_input(f"{m['team_b']}", 0, 20, 0, key=f"b_{mid}")
                        if c3.button("Uložit", key=f"s_{mid}"):
                            def calc(ta, tb, ra, rb):
                                if ta == ra and tb == rb: return 5
                                if (ra-rb) == (ta-tb): return 3
                                if (ra>rb and ta>tb) or (ra<rb and ta<tb): return 2
                                return 0
                            if not df_bets.empty:
                                df_bets['points_earned'] = df_bets.apply(
                                    lambda x: calc(x['tip_a'], x['tip_b'], res_a, res_b) if x['match_id'] == mid else x['points_earned'], axis=1
                                )
                            df_matches.loc[df_matches['match_id'] == mid, ['result_a', 'result_b', 'status']] = [res_a, res_b, 'ukončeno']
                            nt = df_bets.groupby('user_name')['points_earned'].sum().reset_index()
                            df_users = df_users.drop(columns=['total_points']).merge(nt, on='user_name', how='left').fillna(0)
                            df_users.rename(columns={'points_earned': 'total_points'}, inplace=True)
                            conn.update(spreadsheet=URL, worksheet="Bets", data=df_bets)
                            conn.update(spreadsheet=URL, worksheet="Matches", data=df_matches)
                            conn.update(spreadsheet=URL, worksheet="Users", data=df_users)
                            st.cache_data.clear()
                            st.rerun()
        else: st.info("Vše vyhodnoceno.")
        st.stop()

# --- HRÁČSKÉ ROZHRANÍ ---
if st.session_state.user:
    st.title("🏒 Hokejová Tipovačka")
    t1, t2, t3 = st.tabs(["📝 VSADIT SI", "🏆 ŽEBŘÍČEK", "📅 VÝSLEDKY"])
    
    with t1:
        # Zámek 20 min po začátku
        cutoff = datetime.now() - timedelta(minutes=20)
        # Klíčová oprava filtru: status musí
