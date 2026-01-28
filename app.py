import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz

# --- KONFIGURACE ---
PRG = pytz.timezone("Europe/Prague")
URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

st.set_page_config(page_title="Infi Tipovačka 2026", page_icon=LOGO_URL, layout="wide")

# --- GLOBÁLNÍ PŘIPOJENÍ ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CSS STYLY ---
st.markdown(f"""
    <style>
    [data-testid="stSidebar"] {{ display: none; }}
    .match-card {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #6c757d;
    }}
    .match-card-open {{ border-left: 5px solid #28a745; }}
    .status-badge {{
        padding: 3px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: bold;
    }}
    .badge-open {{ background-color: #28a745; color: white; }}
    .badge-locked {{ background-color: #ff4b4b; color: white; }}
    .team-name {{ font-weight: bold; font-size: 1.1rem; }}
    .score-display {{ font-size: 1.8rem; font-weight: 800; color: #ff4b4b; }}
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCE ---
def get_now():
    return datetime.now(PRG)

def get_flag(team):
    d = {"CZE":"cz","SVK":"sk","CAN":"ca","USA":"us","FIN":"fi","SWE":"se","SUI":"ch","GER":"de","LAT":"lv","NOR":"no","DEN":"dk","AUT":"at","FRA":"fr","KAZ":"kz"}
    code = d.get(str(team).strip().upper(), "un")
    return f"https://flagcdn.com/w80/{code}.png"

def calculate_points(tip_a, tip_b, res_a, res_b):
    if tip_a == res_a and tip_b == res_b: return 5
    if (tip_a - tip_b) == (res_a - res_b): return 3
    if (tip_a > tip_b and res_a > res_b) or (tip_a < tip_b and res_a < res_b): return 2
    return 0

@st.cache_data(ttl=5)
def load_data():
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=0).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    
    df_m['match_id'] = df_m['match_id'].astype(str)
    # Převod času
    df_m['internal_datetime'] = pd.to_datetime(
        df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), 
        dayfirst=True
    ).dt.tz_localize(PRG)
    
    return df_m, df_b, df_u

df_m, df_b, df_u = load_data()

# --- SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False
if 'reg_mode' not in st.session_state: st.session_state.reg_mode = None

# --- QR LOGIKA ---
token_url = st.query_params.get("token")
if token_url and not st.session_state.user and not st.session_state.admin:
    user_match = df_u[df_u['token'] == token_url]
    if not user_match.empty:
        u_row = user_match.iloc[0]
        if pd.isna(u_row['user_name']) or str(u_row['user_name']).strip() == "":
            st.session_state.reg_mode = token_url
        else:
            st.session_state.user = u_row['user_name']
            st.rerun()

# --- UI LOGO ---
st.markdown(f'<div style="text-align:center; padding:10px;"><img src="{LOGO_URL}" width="200"></div>', unsafe_allow_html=True)

# --- LOGIN / REGISTRACE ---
if not st.session_state.user and not st.session_state.admin:
    if st.session_state.reg_mode:
        st.subheader("📝 Aktivace QR kódu")
        with st.form("new_player"):
            new_n = st.text_input("Přezdívka").strip()
            new_p = st.text_input("PIN (4 čísla)", type="password", max_chars=4).strip()
            if st.form_submit_button("Začít tipovat"):
                if new_n and len(new_p) == 4:
                    df_u.loc[df_u['token'] == st.session_state.reg_mode, ['user_name', 'pin', 'total_points']] = [new_n, new_p, 0]
                    conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                    st.session_state.user = new_n
                    st.session_state.reg_mode = None
                    st.cache_data.clear()
                    st.rerun()
                else: st.error("Chybné údaje.")
    else:
        tab_log, tab_adm = st.tabs(["🔑 Přihlášení", "🔒 Admin"])
        with tab_log:
            with st.form("manual"):
                u_in = st.text_input("Jméno")
                p_in = st.text_input("PIN", type="password")
                if st.form_submit_button("Vstoupit"):
                    u_row = df_u[df_u['user_name'].str.lower() == u_in.lower().strip()]
                    if not u_row.empty and str(u_row.iloc[0]['pin']) == p_in.strip():
                        st.session_state.user = u_row.iloc[0]['user_name']
                        st.rerun()
                    else: st.error("Chyba.")
        with tab_adm:
            a_pw = st.text_input("Heslo", type="password")
            if st.button("Vstup"):
                if a_pw == "hokej2026":
                    st.session_state.admin = True
                    st.rerun()

# --- ADMIN ---
elif st.session_state.admin:
    if st.button("⬅️ Zpět"): st.session_state.admin = False; st.rerun()
    active = df_m[df_m['status'] != 'ukončeno'].sort_values('internal_datetime')
    for _, m in active.iterrows():
        with st.expander(f"{m['team_a']} vs {m['team_b']}"):
            c1, c2, c3 = st.columns(3)
            rA = c1.number_input("A", 0, 20, key=f"rA{m['match_id']}")
            rB = c2.number_input("B", 0, 20, key=f"rB{m['match_id']}")
            if c3.button("Uložit", key=f"s{m['match_id']}"):
                df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [rA, rB, 'ukončeno']
                if not df_b.empty:
                    m_mask = df_b['match_id'] == m['match_id']
                    df_b.loc[m_mask, 'points_earned'] = df_b[m_mask].apply(lambda x: calculate_points(x['tip_a'], x['tip_b'], rA, rB), axis=1)
                
                # Přepočet bodů (zachování všech sloupců včetně tokenu)
                user_points = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                df_u = df_u.drop(columns=['total_points'], errors='ignore').merge(user_points, on='user_name', how='left').fillna(0).rename(columns={'points_earned':'total_points'})
                
                conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                st.cache_data.clear()
                st.rerun()

# --- HRÁČ ---
else:
    u_row = df_u[df_u['user_name'] == st.session_state.user]
    pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    st.write(f"### 🏒 {st.session_state.user} | {pts} b.")
    if st.button("Odhlásit"): st.session_state.user = None; st.rerun()
    
    t1, t2 = st.tabs(["📝 TIPY", "🏆 POŘADÍ"])
    with t1:
        now = get_now()
        for _, m in df_m.sort_values('internal_datetime').iterrows():
            lock = m['internal_datetime'] + timedelta(minutes=20)
            is_locked, is_done = now > lock, m['status'] == 'ukončeno'
            
            # Badge
            if is_done: status, b_cls = "Hotovo", "badge-locked"
            elif is_locked: status, b_cls = "Zamknuto", "badge-locked"
            else: status, b_cls = "Tipuj!", "badge-open"

            st.markdown(f"""
                <div class="match-card {'match-card-open' if not is_locked else ''}">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span style="font-size:0.8rem; opacity:0.6;">{m['time']}</span>
                        <span class="status-badge {b_cls}">{status}</span>
                    </div>
                    <div style="display:flex; align-items:center; text-align:center;">
                        <div style="flex:1;"><b>{m['team_a']}</b></div>
                        <div style="flex:1;" class="score-display">{"vs" if not is_done else f"{int(m['result_a'])}:{int(m['result_b'])}"}</div>
                        <div style="flex:1;"><b>{m['team_b']}</b></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            u_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == m['match_id'])]
            if not is_locked:
                if not u_bet.empty: st.success(f"Tvůj tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])}")
                else:
                    with st.expander("VSADIT"):
                        with st.form(f"f{m['match_id']}"):
                            c1, c2 = st.columns(2)
                            tA = c1.number_input(str(m['team_a']), 0, 20)
                            tB = c2.number_input(str(m['team_b']), 0, 20)
                            if st.form_submit_button("OK"):
                                new_b = pd.DataFrame([{"timestamp": now.strftime("%H:%M"), "user_name": st.session_state.user, "match_id": m['match_id'], "tip_a": tA, "tip_b": tB, "points_earned": 0}])
                                conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_b, new_b]))
                                st.cache_data.clear(); st.rerun()
            elif not u_bet.empty:
                st.info(f"Tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])}")

    with t2:
        if not df_u.empty:
            lead = df_u[df_u['user_name'] != ""][['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
            lead.index += 1
            st.table(lead)
