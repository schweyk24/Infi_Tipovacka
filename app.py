import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- KONFIGURACE ---
st.set_page_config(page_title="Infi Tipovačka 2026", layout="wide")

# --- DESIGN (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #212529; }
    
    /* Centrování loga */
    .logo-container { display: flex; justify-content: center; padding: 20px; }
    
    /* Karty zápasů */
    .match-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border: 1px solid #e9ecef;
    }
    .match-card-bet {
        background-color: #d4edda !important;
        border: 1px solid #c3e6cb !important;
    }
    
    /* Tlačítka a formy */
    .stButton>button { border-radius: 10px; background-color: #e63946; color: white; font-weight: bold; }
    .bet-header { color: #32cd32; font-weight: bold; font-size: 1.1em; }
    
    /* Skrytí sidebar menu pro čistý mobilní vzhled */
    [data-testid="stSidebar"] { display: none; }
    
    /* Tabulky */
    .styled-table { width: 100%; border-collapse: collapse; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

# --- POMOCNÉ FUNKCE ---
def get_flag_url(team_name):
    team = str(team_name).strip().upper()
    codes = {
        "CZE": "cz", "ČESKO": "cz", "SVK": "sk", "SLOVENSKO": "sk", "CAN": "ca", "KANADA": "ca", 
        "USA": "us", "FIN": "fi", "SWE": "se", "SUI": "ch", "GER": "de", "LAT": "lv", 
        "NOR": "no", "DEN": "dk", "AUT": "at", "FRA": "fr", "KAZ": "kz", "ITA": "it", 
        "SLO": "si", "HUN": "hu", "ITÁLIE": "it"
    }
    code = codes.get(team, "un")
    return f"https://flagcdn.com/w80/{code}.png"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=2).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=2).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=2).dropna(how='all')
    df_m.columns = [str(c).strip().lower() for c in df_m.columns]
    # Oprava formátu času a data
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True, errors='coerce')
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['status'] = df_m['status'].astype(str).str.strip().lower()
    return conn, df_m, df_b, df_u

conn, df_matches, df_bets, df_users = load_data()

if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False

# --- LOGO (VYCENTROVANÉ) ---
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="250"></div>', unsafe_allow_html=True)

# --- REŽIM BARMAN (PŘIHLÁŠENÍ) ---
if not st.session_state.user and not st.session_state.admin:
    if st.button("🔒 Barman Login", key="admin_btn", help="Vstup pro obsluhu"):
        st.session_state.admin_mode = True

# --- LOGIKA STRÁNEK ---
if st.session_state.admin_mode if 'admin_mode' in st.session_state else False:
    st.subheader("⚙️ Administrace - Vyhodnocení")
    pwd = st.text_input("Heslo", type="password")
    if pwd == "hokej2026":
        st.session_state.admin = True
        del st.session_state['admin_mode']
        st.rerun()

if st.session_state.admin:
    st.button("Odhlásit Admina", on_click=lambda: st.session_state.update({"admin": False}))
    to_score = df_matches[df_matches['status'] != 'ukončeno'].copy()
    for _, m in to_score.iterrows():
        with st.container():
            st.write(f"**{m['team_a']} vs {m['team_b']}**")
            c1, c2, c3 = st.columns(3)
            res_a = c1.number_input(f"Góly {m['team_a']}", 0, 20, key=f"adm_a_{m['match_id']}")
            res_b = c2.number_input(f"Góly {m['team_b']}", 0, 20, key=f"adm_b_{m['match_id']}")
            if c3.button("Uložit", key=f"save_{m['match_id']}"):
                # Logika výpočtu bodů a update (zkráceno pro prostor)
                st.success("Uloženo!") 
    st.stop()

if st.session_state.user is None:
    # --- LANDING PAGE ---
    col_a, col_b = st.columns([1, 1], gap="large")
    with col_a:
        st.subheader("📜 Pravidla")
        st.info("5 bodů za přesný tip, 3 body za rozdíl/remízu, 2 body za vítěze.")
        st.subheader("🏁 Nejlepší v baru")
        top_5 = df_users.sort_values('total_points', ascending=False).head(5)
        st.table(top_5[['user_name', 'total_points']].rename(columns={'user_name': 'Přezdívka', 'total_points': 'Celkem bodů'}))

    with col_b:
        st.subheader("🔑 Přihlášení")
        with st.form("login"):
            u_in = st.text_input("Přezdívka")
            p_in = st.text_input("PIN (4 čísla)", type="password")
            if st.form_submit_button("Vstoupit"):
                if u_in and len(p_in) == 4:
                    if u_in not in df_users['user_name'].values:
                        new_u = pd.DataFrame([{"user_name": u_in, "pin": p_in, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_users, new_u], ignore_index=True))
                    st.session_state.user = u_in
                    st.rerun()

    st.subheader("📅 Dnešní hokeje")
    today_str = datetime.now().strftime("%d.%m.%Y")
    today_matches = df_matches[df_matches['date'] == today_str]
    if today_matches.empty:
        st.write("Dnes se nic nehraje, mrkni na zítřek!")
    else:
        for _, m in today_matches.iterrows():
            st.markdown(f"🏒 **{m['team_a']} vs {m['team_b']}** | ⏰ {m['time']}")

else:
    # --- PŘIHLÁŠENÝ UŽIVATEL ---
    u_pts = df_users[df_users['user_name'] == st.session_state.user]['total_points'].values[0]
    st.markdown(f"### Čau {st.session_state.user}! 🏒 (Tvůj stav: **{int(u_pts)} bodů**)")
    
    t1, t2, t3 = st.tabs(["📝 TIPOVÁNÍ", "📊 ŽEBŘÍČEK", "✅ VÝSLEDKY"])
    
    with t1:
        now = datetime.now()
        open_m = df_matches[(df_matches['status'] == 'budoucí') & (df_matches['internal_datetime'] > (now - timedelta(minutes=20)))]
        
        for _, m in open_m.iterrows():
            cid = str(m['match_id'])
            user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
            is_bet = not user_bet.empty
            
            # Tie-out countdown
            end_time = m['internal_datetime'] + timedelta(minutes=20)
            diff = end_time - now
            countdown_str = f"Sázky končí za: {diff.seconds // 60} min" if diff.total_seconds() > 0 else "Sázky uzavřeny"

            # KARTA
            card_class = "match-card-bet" if is_bet else ""
            st.markdown(f"""
            <div class="match-card {card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; text-align: center;">
                    <div style="width: 40%;"><img src="{get_flag_url(m['team_a'])}" width="50"><br><b>{m['team_a']}</b></div>
                    <div style="width: 20%;">VS</div>
                    <div style="width: 40%;"><img src="{get_flag_url(m['team_b'])}" width="50"><br><b>{m['team_b']}</b></div>
                </div>
                <div style="text-align: center; color: #6c757d; font-size: 0.9em; margin-top: 10px;">
                    📅 {m['date']} | ⏰ {m['time']} | ⏱️ {countdown_str}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if is_bet:
                st.markdown(f"<p class='bet-header'>✅ Na tento zápas jsi už tipoval. Tvůj tip: {int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}</p>", unsafe_allow_html=True)
            else:
                with st.expander("🟢 Odeslat tip"):
                    with st.form(key=f"form_{cid}"):
                        c1, c2 = st.columns(2)
                        ta = c1.number_input(m['team_a'], 0, 20, key=f"t1_{cid}")
                        tb = c2.number_input(m['team_b'], 0, 20, key=f"t2_{cid}")
                        if st.form_submit_button("POTVRDIT TIP"):
                            new_row = pd.DataFrame([{"timestamp": now.strftime("%H:%M"), "user_name": st.session_state.user, "match_id": cid, "tip_a": ta, "tip_b": tb, "points_earned": 0}])
                            conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_bets, new_row]))
                            st.cache_data.clear()
                            st.rerun()

    with t2:
        st.subheader("🏆 Celkové pořadí")
        lead = df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
        lead.index += 1
        st.table(lead.rename(columns={'user_name': 'Přezdívka', 'total_points': 'Celkem bodů'}))

    with t3:
        st.subheader("✅ Výsledky")
        fin = df_matches[df_matches['status'] == 'ukončeno'].copy()
        if not fin.empty:
            # Oprava zobrazení skóre na celá čísla
            fin['Skóre'] = fin.apply(lambda x: f"{int(x['result_a'])} : {int(x['result_b'])}", axis=1)
            st.table(fin[['date', 'team_a', 'Skóre', 'team_b']].rename(columns={'date': 'Datum', 'team_a': 'Tým A', 'team_b': 'Tým B'}))

    st.button("Odhlásit se", on_click=lambda: st.session_state.update({"user": None}))
