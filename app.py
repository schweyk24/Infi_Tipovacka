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
    @media (prefers-color-scheme: light) {{
        .match-card {{ background: #ffffff; border: 1px solid #eee; color: #1a1a1a; }}
    }}
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

@st.cache_data(ttl=10)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=0).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True).dt.tz_localize(PRG)
    return conn, df_m, df_b, df_u

conn, df_m, df_b, df_u = load_data()

# --- AUTENTIZACE PŘES URL (QR TOKEN) ---
if 'user' not in st.session_state:
    token_url = st.query_params.get("token")
    if token_url and not df_u.empty:
        user_match = df_u[df_u['token'] == token_url]
        if not user_match.empty:
            # Token existuje
            u_row = user_match.iloc[0]
            if pd.isna(u_row['user_name']) or u_row['user_name'] == "":
                st.session_state.reg_mode = token_url # Povolíme registraci pro tento prázdný token
            else:
                st.session_state.user = u_row['user_name'] # Automatický login
                st.rerun()

if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False

# --- UI - LOGO ---
st.markdown(f'<div style="text-align:center; padding:20px;"><img src="{LOGO_URL}" width="220"></div>', unsafe_allow_html=True)

# --- 1. LOGIN / REGISTRACE ---
if not st.session_state.user and not st.session_state.admin:
    
    if st.session_state.get('reg_mode'):
        st.subheader("📝 Registrace nového hráče")
        with st.form("new_player"):
            new_n = st.text_input("Tvoje přezdívka (viditelná v žebříčku)").strip()
            new_p = st.text_input("PIN (4 čísla - pro ruční přihlášení)", type="password", max_chars=4).strip()
            new_e = st.text_input("E-mail (pro kontakt výherce)").strip()
            if st.form_submit_button("Aktivovat můj QR kód"):
                if new_n and len(new_p) == 4:
                    # Najdeme řádek s tokenem a aktualizujeme ho
                    mask = df_u['token'] == st.session_state.reg_mode
                    df_u.loc[mask, ['user_name', 'pin', 'email', 'total_points']] = [new_n, new_p, new_e, 0]
                    conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                    st.session_state.user = new_n
                    st.session_state.reg_mode = None
                    st.cache_data.clear()
                    st.rerun()
                else: st.error("Vyplň jméno a 4místný PIN.")
    else:
        tab_log, tab_info, tab_adm = st.tabs(["🔑 Přihlášení", "ℹ️ Jak hrát", "🔒 Admin"])
        with tab_log:
            with st.form("manual_login"):
                u_in = st.text_input("Přezdívka")
                p_in = st.text_input("PIN", type="password")
                if st.form_submit_button("Vstoupit"):
                    user_row = df_u[df_u['user_name'].str.lower() == u_in.lower().strip()]
                    if not user_row.empty and str(user_row.iloc[0]['pin']) == p_in.strip():
                        st.session_state.user = user_row.iloc[0]['user_name']
                        st.rerun()
                    else: st.error("Chybné jméno nebo PIN.")
        with tab_info:
            st.info("Skenuj svůj unikátní QR kód pro automatické přihlášení. Pokud ho nemáš, vyžádej si ho u obsluhy.")
        with tab_adm:
            a_pw = st.text_input("Heslo", type="password")
            if st.button("Vstup pro personál"):
                if a_pw == "hokej2026":
                    st.session_state.admin = True
                    st.rerun()

# --- 2. ADMIN SEKCE ---
elif st.session_state.admin:
    st.title("⚙️ Admin Panel")
    if st.button("⬅️ Zpět"): st.session_state.admin = False; st.rerun()
    
    # Vyhodnocení (zkrácená verze tvé logiky)
    active = df_m[df_m['status'] != 'ukončeno'].sort_values('internal_datetime')
    for _, m in active.iterrows():
        with st.expander(f"Zapsat skóre: {m['team_a']} vs {m['team_b']}"):
            c1, c2, c3 = st.columns(3)
            rA = c1.number_input("A", 0, 20, key=f"rA{m['match_id']}")
            rB = c2.number_input("B", 0, 20, key=f"rB{m['match_id']}")
            if c3.button("Uložit", key=f"s{m['match_id']}"):
                df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [rA, rB, 'ukončeno']
                if not df_b.empty:
                    df_b['points_earned'] = df_b.apply(lambda x: calculate_points(x['tip_a'], x['tip_b'], rA, rB) if x['match_id'] == m['match_id'] else x['points_earned'], axis=1)
                user_sums = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                df_u = df_u.drop(columns=['total_points'], errors='ignore').merge(user_sums, on='user_name', how='left').fillna(0).rename(columns={'points_earned': 'total_points'})
                conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                st.cache_data.clear(); st.rerun()

# --- 3. HRÁČSKÁ SEKCE ---
else:
    u_row = df_u[df_u['user_name'] == st.session_state.user]
    pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    
    st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center;'><h3>🏒 {st.session_state.user}</h3><h2 style='color:#ff4b4b; margin:0;'>{pts} b.</h2></div>", unsafe_allow_html=True)
    if st.button("Odhlásit"): st.session_state.user = None; st.rerun()
    
    t1, t2 = st.tabs(["📝 TIPOVÁNÍ", "🏆 ŽEBŘÍČEK"])
    
    with t1:
        now = get_now()
        for _, m in df_m.sort_values('internal_datetime').iterrows():
            lock_time = m['internal_datetime'] + timedelta(minutes=20)
            is_locked = now > lock_time
            is_done = m['status'] == 'ukončeno'
            
            # Status badge
            if is_done: status, b_cls = "Hotovo", "badge-locked"
            elif is_locked: status, b_cls = "Zamknuto", "badge-locked"
            else:
                rem = lock_time - now
                status = f"Tipuj! (+{int(rem.total_seconds()//60)}m)" if now > m['internal_datetime'] else f"Start {m['time']}"
                b_cls = "badge-open"

            st.markdown(f"""
                <div class="match-card {'match-card-open' if not is_locked else ''}">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span style="font-size:0.8rem; opacity:0.6;">{m['date']}</span>
                        <span class="status-badge {b_cls}">{status}</span>
                    </div>
                    <div style="display:flex; align-items:center; text-align:center;">
                        <div style="flex:1;"><img src="{get_flag(m['team_a'])}" width="35"><br><span class="team-name">{m['team_a']}</span></div>
                        <div style="flex:1;" class="score-display">{"vs" if not is_done else f"{int(m['result_a'])}:{int(m['result_b'])}"}</div>
                        <div style="flex:1;"><img src="{get_flag(m['team_b'])}" width="35"><br><span class="team-name">{m['team_b']}</span></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            u_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == m['match_id'])]
            
            if not is_locked:
                if not u_bet.empty:
                    st.success(f"Tvůj tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])}")
                else:
                    with st.expander("PODAT TIP"):
                        with st.form(key=f"f{m['match_id']}"):
                            c1, c2 = st.columns(2)
                            tA = c1.number_input(str(m['team_a']), 0, 20, key=f"tA{m['match_id']}")
                            tB = c2.number_input(str(m['team_b']), 0, 20, key=f"tB{m['match_id']}")
                            if st.form_submit_button("Odeslat tip"):
                                new_b = pd.DataFrame([{"timestamp": now.strftime("%H:%M"), "user_name": st.session_state.user, "match_id": m['match_id'], "tip_a": tA, "tip_b": tB, "points_earned": 0}])
                                conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_b, new_b]))
                                st.cache_data.clear(); st.rerun()
            elif is_done and not u_bet.empty:
                st.info(f"Tvůj tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])} | Zisk: {int(u_bet.iloc[0]['points_earned'])} b.")

    with t2:
        if not df_u.empty:
            lead = df_u[df_u['user_name'] != ""][['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
            lead.index += 1
            st.table(lead.rename(columns={'user_name':'Hráč','total_points':'Body'}))
