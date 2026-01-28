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
        text-transform: uppercase;
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

# --- POMOCNÉ FUNKCE ---
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
    
    for df in [df_b, df_u]:
        if not df.empty and 'user_name' in df.columns:
            df['user_name'] = df['user_name'].astype(str).str.strip()
    return conn, df_m, df_b, df_u

conn, df_m, df_b, df_u = load_data()

# --- SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False

# --- LOGO ---
st.markdown(f'<div style="text-align:center"><img src="{LOGO_URL}" width="200"></div>', unsafe_allow_html=True)

# --- 1. LOGIN / REGISTRACE ---
if not st.session_state.user and not st.session_state.admin:
    st.markdown("<h3 style='text-align:center;'>Vítejte v Infi Baru! 🍻</h3>", unsafe_allow_html=True)
    
    tab_log, tab_reg, tab_adm = st.tabs(["🔑 Přihlášení", "📝 Registrace", "🔒 Admin"])
    
    with tab_log:
        with st.form("login"):
            u_in = st.text_input("Přezdívka")
            p_in = st.text_input("PIN", type="password")
            if st.form_submit_button("Vstoupit"):
                user_row = df_u[df_u['user_name'].str.lower() == u_in.lower().strip()]
                if not user_row.empty and str(user_row.iloc[0]['pin']) == p_in.strip():
                    st.session_state.user = user_row.iloc[0]['user_name']
                    st.rerun()
                else: st.error("Chybné jméno nebo PIN.")

    with tab_reg:
        with st.form("reg"):
            u_r = st.text_input("Nová přezdívka")
            p_r = st.text_input("PIN (4 čísla)", max_chars=4)
            ph_r = st.text_input("Poslední 3 čísla mobilu (pro obnovu)", max_chars=3)
            if st.form_submit_button("Vytvořit účet"):
                if u_r and len(p_r) == 4 and len(ph_r) == 3:
                    if u_r.lower() in df_u['user_name'].str.lower().values:
                        st.warning("Jméno je obsazené.")
                    else:
                        new_u = pd.DataFrame([{"user_name": u_r, "pin": p_r, "phone_last": ph_r, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_u, new_u]))
                        st.success("Hotovo! Teď se přihlas.")
                else: st.error("Vyplň vše správně.")

    with tab_adm:
        a_pw = st.text_input("Admin heslo", type="password")
        if st.button("Vstup pro personál"):
            if a_pw == "hokej2026": # Zde doporučuji st.secrets
                st.session_state.admin = True
                st.rerun()

# --- 2. ADMIN SEKCE ---
elif st.session_state.admin:
    st.title("⚙️ Administrace")
    if st.button("Odhlásit"): st.session_state.admin = False; st.rerun()
    
    t_score, t_matches = st.tabs(["Vyhodnocení", "Správa zápasů"])
    
    with t_score:
        active = df_m[df_m['status'] != 'ukončeno'].sort_values('internal_datetime')
        for _, m in active.iterrows():
            with st.expander(f"Zapsat výsledek: {m['team_a']} vs {m['team_b']}"):
                c1, c2, c3 = st.columns(3)
                res_a = c1.number_input("Skóre A", 0, 20, key=f"ra{m['match_id']}")
                res_b = c2.number_input("Skóre B", 0, 20, key=f"rb{m['match_id']}")
                if c3.button("Uložit a obodovat", key=f"btn{m['match_id']}"):
                    # 1. Update zápasu
                    df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [res_a, res_b, 'ukončeno']
                    # 2. Update bodů v sázkách
                    if not df_b.empty:
                        mask = df_b['match_id'] == m['match_id']
                        df_b.loc[mask, 'points_earned'] = df_b[mask].apply(lambda x: calculate_points(x['tip_a'], x['tip_b'], res_a, res_b), axis=1)
                    # 3. Přepočet celkových bodů uživatelů
                    user_sums = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                    df_u_new = df_u.drop(columns=['total_points']).merge(user_sums, on='user_name', how='left').fillna(0)
                    df_u_new = df_u_new.rename(columns={'points_earned': 'total_points'})
                    
                    conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                    conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                    conn.update(spreadsheet=URL, worksheet="Users", data=df_u_new)
                    st.cache_data.clear()
                    st.success("Zápas vyhodnocen!")
                    st.rerun()

# --- 3. HRÁČSKÁ SEKCE ---
else:
    u_data = df_u[df_u['user_name'] == st.session_state.user]
    pts = int(u_data['total_points'].values[0]) if not u_data.empty else 0
    
    st.markdown(f"### 🏒 {st.session_state.user} | <span style='color:#ff4b4b'>{pts} bodů</span>", unsafe_allow_html=True)
    if st.button("Odhlásit", size="small"): st.session_state.user = None; st.rerun()
    
    t_matches, t_leader = st.tabs(["📋 Zápasy", "🏆 Žebříček"])
    
    with t_matches:
        now = get_now()
        for _, m in df_m.sort_values('internal_datetime').iterrows():
            lock_time = m['internal_datetime'] + timedelta(minutes=20)
            is_locked = now > lock_time
            is_done = m['status'] == 'ukončeno'
            
            # Status Badge Logic
            if is_done: status, b_cls = "Ukončeno", "badge-locked"
            elif is_locked: status, b_cls = "Probíhá (Zamknuto)", "badge-locked"
            else:
                rem = lock_time - now
                mins = int(rem.total_seconds() // 60)
                status = f"Tipuj! Končí za {mins}m" if now > m['internal_datetime'] else f"Začíná {m['date']} {m['time']}"
                b_cls = "badge-open"

            card_style = "match-card-open" if not is_locked else ""
            
            st.markdown(f"""
                <div class="match-card {card_style}">
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span style="font-size:0.8rem; opacity:0.8;">ID: {m['match_id']}</span>
                        <span class="status-badge {b_cls}">{status}</span>
                    </div>
                    <div style="display:flex; align-items:center; text-align:center;">
                        <div style="flex:1;"><img src="{get_flag(m['team_a'])}" width="40"><br><span class="team-name">{m['team_a']}</span></div>
                        <div style="flex:1;" class="score-display">{"?" if not is_done else f"{int(m['result_a'])}:{int(m['result_b'])}"}</div>
                        <div style="flex:1;"><img src="{get_flag(m['team_b'])}" width="40"><br><span class="team-name">{m['team_b']}</span></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Sázecí logika
            u_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == m['match_id'])]
            
            if not is_locked:
                if not u_bet.empty:
                    st.success(f"Tvůj tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])}")
                else:
                    with st.expander("Odeslat tip"):
                        with st.form(key=f"f{m['match_id']}"):
                            c1, c2 = st.columns(2)
                            tA = c1.number_input(str(m['team_a']), 0, 20, key=f"tA{m['match_id']}")
                            tB = c2.number_input(str(m['team_b']), 0, 20, key=f"tB{m['match_id']}")
                            if st.form_submit_button("Potvrdit tip"):
                                new_b = pd.DataFrame([{"timestamp": now.strftime("%H:%M"), "user_name": st.session_state.user, "match_id": m['match_id'], "tip_a": tA, "tip_b": tB, "points_earned": 0}])
                                conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_b, new_b]))
                                st.cache_data.clear()
                                st.rerun()
            else:
                if not u_bet.empty:
                    pts_get = int(u_bet.iloc[0]['points_earned']) if is_done else "?"
                    st.info(f"Tvůj tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])} | Zisk: {pts_get} b.")
                else:
                    st.warning("Zápas probíhá nebo skončil bez tvého tipu.")

    with t_leader:
        st.subheader("🏆 Aktuální pořadí")
        leaderboard = df_u[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
        leaderboard.index += 1
        st.table(leaderboard.rename(columns={'user_name':'Hráč', 'total_points':'Body'}))
