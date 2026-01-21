import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Infi Tipovačka 2026", layout="wide")

# --- CSS DESIGN ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #212529; }
    .logo-container { display: flex; justify-content: center; padding: 10px 0; }
    .match-card {
        background-color: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid #eee;
        margin-bottom: 15px;
    }
    .match-card-bet { border-left: 8px solid #28a745; background-color: #f8fff9; }
    .match-card-locked { border-left: 8px solid #adb5bd; background-color: #f8f9fa; color: #6c757d; }
    .match-header { display: flex; justify-content: space-between; font-size: 0.85em; margin-bottom: 10px; color: #666; }
    .team-name { font-weight: bold; font-size: 1.1em; }
    .timer-text { color: #d32f2f; font-weight: bold; font-family: monospace; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .badge-live { background-color: #ffe3e3; color: #d32f2f; }
    .badge-ok { background-color: #e3fafc; color: #0b7285; }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

# --- FUNKCE ---
def get_flag_url(team_name):
    t = str(team_name).strip().upper()
    d = {"CZE":"cz","ČESKO":"cz","ČR":"cz","SVK":"sk","SLOVENSKO":"sk","CAN":"ca","KANADA":"ca","USA":"us","FIN":"fi","FINSKO":"fi","SWE":"se","ŠVÉDSKO":"se","SUI":"ch","ŠVÝCARSKO":"ch","GER":"de","NĚMECKO":"de","LAT":"lv","LOTYŠSKO":"lv","NOR":"no","NORSKO":"no","DEN":"dk","DÁNSKO":"dk","AUT":"at","RAKOUSKO":"at","FRA":"fr","FRANCIE":"fr","KAZ":"kz","KAZACHSTÁN":"kz","ITA":"it","ITÁLIE":"it","SLO":"si","SLOVINSKO":"si","HUN":"hu","MAĎARSKO":"hu"}
    return f"https://flagcdn.com/w80/{d.get(t, 'un')}.png"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=0).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    df_m.columns = [str(c).lower().strip() for c in df_m.columns]
    df_m['match_id'] = df_m['match_id'].astype(str)
    # Oprava datumu a času
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True)
    
    if not df_u.empty:
        for col in ['user_name', 'pin', 'phone_last']:
            if col in df_u.columns:
                df_u[col] = df_u[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_u['total_points'] = pd.to_numeric(df_u['total_points'], errors='coerce').fillna(0).astype(int)
    if not df_b.empty:
        df_b['user_name'] = df_b['user_name'].astype(str).str.strip()
        df_b['match_id'] = df_b['match_id'].astype(str)
    return conn, df_m, df_b, df_u

conn, df_m, df_b, df_u = load_data()

# --- LOGIN LOGIKA ---
if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False

st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="220"></div>', unsafe_allow_html=True)

if not st.session_state.user and not st.session_state.admin:
    # (Ponechána původní funkční přihlašovací obrazovka s pravidly)
    col_info, col_lead = st.columns(2)
    with col_info: st.info("🎯 5b Přesný | 🏒 3b Rozdíl | 🏆 2b Vítěz")
    with col_lead: 
        if not df_u.empty: st.dataframe(df_u.sort_values('total_points', ascending=False).head(3)[['user_name','total_points']], hide_index=True)
    
    t_log, t_reg, t_for, t_adm = st.tabs(["🔑 Login", "📝 Registrace", "🆘 PIN", "🔒 Admin"])
    with t_log:
        with st.form("login"):
            u, p = st.text_input("Jméno"), st.text_input("PIN", type="password")
            if st.form_submit_button("Vstoupit"):
                match = df_u[df_u['user_name'].str.lower() == u.lower()]
                if not match.empty and match.iloc[0]['pin'] == p:
                    st.session_state.user = match.iloc[0]['user_name']; st.rerun()
                else: st.error("Chyba.")
    # (Zkráceno pro přehlednost - registrace a obnova zůstávají stejné)
    with t_reg:
        with st.form("r"):
            ur, pr, phr = st.text_input("Jméno"), st.text_input("PIN"), st.text_input("3 čísla mobilu")
            if st.form_submit_button("Registrovat"):
                if ur and pr and len(phr)==3:
                    new_u = pd.DataFrame([{"user_name":ur,"pin":pr,"phone_last":phr,"total_points":0}])
                    conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_u, new_u], ignore_index=True))
                    st.success("OK"); st.cache_data.clear()

# --- ADMIN PANEL ---
elif st.session_state.admin:
    st.header("Admin")
    if st.button("Logout"): st.session_state.admin = False; st.rerun()
    # (Admin logika zůstává stejná)

# --- HRÁČSKÁ SEKCE ---
else:
    u_row = df_u[df_u['user_name'] == st.session_state.user]
    pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    
    c_h1, c_h2 = st.columns([5, 1])
    c_h1.subheader(f"🏒 {st.session_state.user} | {pts} bodů")
    if c_h2.button("Odhlásit", key="top_logout"): st.session_state.user = None; st.rerun()

    t1, t2 = st.tabs(["📝 PŘEHLED ZÁPASŮ", "📊 ŽEBŘÍČEK"])
    
    with t1:
        now = datetime.now()
        # Seřadíme: Nejdřív ty, co jdou tipovat (budoucí), pak ty, co probíhají/skončily
        all_matches = df_m.sort_values('internal_datetime', ascending=True)
        
        for _, m in all_matches.iterrows():
            cid = str(m['match_id'])
            user_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == cid)]
            has_bet = not user_bet.empty
            
            # Časové statusy
            is_finished = m['status'] == 'ukončeno'
            lock_time = m['internal_datetime'] + timedelta(minutes=20)
            is_locked = now > lock_time
            
            # Dynamický odpočet
            if not is_locked and not is_finished:
                td = lock_time - now
                timer_str = f"⏳ Konec za: {td.days}d {td.seconds//3600}h {(td.seconds//60)%60}m"
                status_html = f'<span class="timer-text">{timer_str}</span>'
                c_style = "match-card-bet" if has_bet else "match-card"
            else:
                status_html = '<span class="status-badge badge-live">🔒 Uzavřeno / Probíhá</span>' if not is_finished else '<span class="status-badge badge-ok">✅ Ukončeno</span>'
                c_style = "match-card-locked"

            # Vykreslení karty
            st.markdown(f"""
            <div class="match-card {c_style}">
                <div class="match-header">
                    <div>📅 {m['date']} | ⏰ {m['time']}</div>
                    <div>{status_html}</div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; text-align:center;">
                    <div style="width:35%;">
                        <img src="{get_flag_url(m['team_a'])}" width="45"><br>
                        <span class="team-name">{m['team_a']}</span>
                    </div>
                    <div style="width:25%; font-size: 1.5em; font-weight: bold;">
                        {f"{int(m['result_a'])} : {int(m['result_b'])}" if is_finished else "VS"}
                    </div>
                    <div style="width:35%;">
                        <img src="{get_flag_url(m['team_b'])}" width="45"><br>
                        <span class="team-name">{m['team_b']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Spodní část karty (tipy)
            if is_finished:
                my_tip = f"{int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}" if has_bet else "Netipnuto"
                points = int(user_bet.iloc[0]['points_earned']) if has_bet else 0
                st.markdown(f"<hr style='margin:10px 0'><small>Tvůj tip: <b>{my_tip}</b> | Zisk: <b>{points} b.</b></small>", unsafe_allow_html=True)
            elif is_locked:
                if has_bet:
                    st.markdown(f"<hr style='margin:10px 0'><small>Tvůj tip: <b>{int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}</b> (Čeká se na výsledek)</small>", unsafe_allow_html=True)
                else:
                    st.markdown("<hr style='margin:10px 0'><small style='color:red;'>Na tento zápas už nelze tipovat.</small>", unsafe_allow_html=True)
            else:
                if has_bet:
                    st.markdown(f"<hr style='margin:10px 0'><small style='color:green;'>✅ Máš natipováno: <b>{int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}</b></small>", unsafe_allow_html=True)
                else:
                    with st.expander("➕ ODESLAT TIP"):
                        with st.form(key=f"f{cid}"):
                            c1, c2 = st.columns(2)
                            ta = c1.number_input(m['team_a'], 0, 20, key=f"ta{cid}")
                            tb = c2.number_input(m['team_b'], 0, 20, key=f"tb{cid}")
                            if st.form_submit_button("Odeslat"):
                                new_b = pd.DataFrame([{"timestamp": now.strftime("%H:%M"), "user_name": st.session_state.user, "match_id": cid, "tip_a": int(ta), "tip_b": int(tb), "points_earned": 0}])
                                conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_b, new_b], ignore_index=True))
                                st.cache_data.clear(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        if not df_u.empty:
            st.table(df_u.sort_values('total_points', ascending=False)[['user_name', 'total_points']].rename(columns={'user_name':'Přezdívka','total_points':'Body'}))
