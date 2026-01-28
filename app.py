import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

# --- KONFIGURACE ---
PRG = pytz.timezone("Europe/Prague")
URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

st.set_page_config(page_title="Infi Tipovačka 2026", page_icon=LOGO_URL, layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FORCE LIGHT DESIGN ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    .match-card {
        background: #fdfdfd;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid #e0e0e0;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .status-badge { padding: 4px 8px; border-radius: 5px; font-size: 0.7rem; font-weight: bold; }
    .badge-open { background-color: #d4edda; color: #155724; }
    .badge-locked { background-color: #f8d7da; color: #721c24; }
    .team-name { font-weight: bold; font-size: 1rem; color: #000; }
    .score-display { font-size: 1.5rem; font-weight: 800; color: #d9534f; }
    h1, h2, h3, p, span, label, div { color: #000000 !important; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIKA BODOVÁNÍ (OPRAVENÁ) ---
def calculate_points(tip_a, tip_b, res_a, res_b, in_bar=False):
    pts = 0
    # Hokejové body
    if tip_a == res_a and tip_b == res_b: pts = 5
    elif (tip_a - tip_b) == (res_a - res_b): pts = 3
    elif (tip_a > tip_b and res_a > res_b) or (tip_a < tip_b and res_a < res_b): pts = 2
    
    # BONUS +2 body vždy, když je v baru (nezávisle na tipu)
    if in_bar: pts += 2 
    return pts

@st.cache_data(ttl=5)
def load_data():
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=0).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True).dt.tz_localize(PRG)
    return df_m, df_b, df_u

df_m, df_b, df_u = load_data()

# --- SESSION & QR ---
if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False
if 'reg_mode' not in st.session_state: st.session_state.reg_mode = None

token_url = st.query_params.get("token")
if token_url and not st.session_state.user:
    u_match = df_u[df_u['token'] == token_url]
    if not u_match.empty:
        row = u_match.iloc[0]
        if pd.isna(row['user_name']) or str(row['user_name']).strip() == "":
            st.session_state.reg_mode = token_url
        else:
            st.session_state.user = row['user_name']
            st.rerun()

# --- HOME PAGE ---
if not st.session_state.user and not st.session_state.admin:
    st.image(LOGO_URL, width=150)
    t_h, t_l, t_p, t_a = st.tabs(["🏠 Dnes", "🔑 Vstup", "📜 Pravidla", "🔒 Admin"])
    
    with t_h:
        st.subheader("Dnešní zápasy")
        dnes = df_m[df_m['date'] == datetime.now(PRG).strftime("%d.%m.%Y")]
        if dnes.empty: st.write("Dnes žádný hokej.")
        for _, m in dnes.iterrows():
            st.write(f"**{m['time']}** | {m['team_a']} vs {m['team_b']} ({m['group']})")
        st.divider()
        st.subheader("TOP 5 hráčů")
        if not df_u.empty:
            st.dataframe(df_u[df_u['user_name']!=""].sort_values('total_points', ascending=False)[['user_name', 'total_points']].head(5), hide_index=True)

    with t_l:
        if st.session_state.reg_mode:
            with st.form("reg"):
                n_n = st.text_input("Přezdívka")
                n_p = st.text_input("PIN (4 čísla)", type="password")
                if st.form_submit_button("Registrovat"):
                    df_u.loc[df_u['token'] == st.session_state.reg_mode, ['user_name', 'pin', 'total_points']] = [n_n, n_p, 0]
                    conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                    st.session_state.user = n_n
                    st.rerun()
        else:
            with st.form("log"):
                u_i = st.text_input("Jméno")
                p_i = st.text_input("PIN", type="password")
                if st.form_submit_button("Přihlásit"):
                    match = df_u[df_u['user_name'].str.lower() == u_i.lower().strip()]
                    if not match.empty and str(match.iloc[0]['pin']) == p_i.strip():
                        st.session_state.user = match.iloc[0]['user_name']
                        st.rerun()

    with t_p:
        if os.path.exists("pravidla.md"):
            with open("pravidla.md", "r", encoding="utf-8") as f: st.markdown(f.read())

    with t_a:
        if st.text_input("Admin", type="password") == "hokej2026":
            if st.button("Vstoupit"): st.session_state.admin = True; st.rerun()

# --- PLAYER UI ---
elif st.session_state.user:
    st.write(f"Hráč: **{st.session_state.user}**")
    if st.button("Odhlásit"): st.session_state.user = None; st.rerun()
    
    t_t, t_z = st.tabs(["🏒 Tipovat", "🏆 Žebříček"])
    
    with t_t:
        for _, m in df_m.sort_values('internal_datetime').iterrows():
            lock = m['internal_datetime'] + timedelta(minutes=20)
            is_locked = datetime.now(PRG) > lock
            is_done = m['status'] == 'ukončeno'
            
            st.markdown(f"""
                <div class="match-card">
                    <div style="font-size:0.7rem; color:gray;">{m['date']} | {m['group']}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="team-name">{m['team_a']}</span>
                        <span class="score-display">{"vs" if not is_done else f"{int(m['result_a'])}:{int(m['result_b'])}"}</span>
                        <span class="team-name">{m['team_b']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            u_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == m['match_id'])]
            
            if not is_locked:
                if not u_bet.empty:
                    st.success(f"Tvůj tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])} {'(BONUS ✅)' if u_bet.iloc[0]['in_bar'] else ''}")
                else:
                    with st.expander("Vsadit"):
                        with st.form(f"b{m['match_id']}"):
                            c1, c2 = st.columns(2)
                            tA = c1.number_input("A", 0, 20)
                            tB = c2.number_input("B", 0, 20)
                            code = st.text_input("Kód z baru").strip()
                            if st.form_submit_button("Odeslat"):
                                in_b = (code.upper() == str(m['bar_code_day']).upper())
                                new = pd.DataFrame([{"user_name": st.session_state.user, "match_id": m['match_id'], "tip_a": tA, "tip_b": tB, "points_earned": 0, "in_bar": in_b}])
                                conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_b, new]))
                                st.cache_data.clear(); st.rerun()

    with t_z:
        st.dataframe(df_u[df_u['user_name']!=""].sort_values('total_points', ascending=False)[['user_name', 'total_points']], hide_index=True)

# --- ADMIN UI ---
elif st.session_state.admin:
    st.button("Zpět", on_click=lambda: setattr(st.session_state, 'admin', False))
    to_eval = df_m[df_m['status'] != 'ukončeno']
    for _, m in to_eval.iterrows():
        with st.expander(f"{m['team_a']} - {m['team_b']}"):
            res_a = st.number_input("Skóre A", 0, 20, key=f"ra{m['match_id']}")
            res_b = st.number_input("Skóre B", 0, 20, key=f"rb{m['match_id']}")
            if st.button("Uložit výsledek", key=f"btn{m['match_id']}"):
                df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [res_a, res_b, 'ukončeno']
                if not df_b.empty:
                    m_mask = df_b['match_id'] == m['match_id']
                    df_b.loc[m_mask, 'points_earned'] = df_b[m_mask].apply(lambda x: calculate_points(x['tip_a'], x['tip_b'], res_a, res_b, x['in_bar']), axis=1)
                
                # Přepočet celkových bodů
                sums = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                df_u = df_u.drop(columns=['total_points'], errors='ignore').merge(sums, on='user_name', how='left').fillna(0).rename(columns={'points_earned':'total_points'})
                
                conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                st.cache_data.clear(); st.rerun()
