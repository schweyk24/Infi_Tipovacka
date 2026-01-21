import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Infi Tipovačka 2026", layout="wide")

# --- DESIGN (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #212529; }
    .logo-container { display: flex; justify-content: center; padding: 20px 0; }
    
    /* Karty zápasů a rozestupy */
    .match-wrapper { margin-bottom: 40px; padding-bottom: 20px; border-bottom: 2px solid #eee; }
    .match-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
        border: 1px solid #e9ecef;
    }
    .match-card-bet {
        background-color: #e8f5e9 !important;
        border: 2px solid #2e7d32 !important;
    }
    
    /* Hlášky a texty */
    .bet-confirmed { color: #2e7d32; font-weight: bold; font-size: 1.1em; padding: 10px 0; }
    .stExpander { border: none !important; box-shadow: none !important; }
    .stExpander summary { color: #2e7d32 !important; font-weight: bold; border: 1px solid #2e7d32; border-radius: 8px; padding: 5px 15px; }

    /* Skrytí sidebar */
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

# --- POMOCNÉ FUNKCE ---
def get_flag_url(team_name):
    team = str(team_name).strip().upper()
    # Rozšířený slovník pro všechny varianty
    codes = {
        "CZE": "cz", "ČESKO": "cz", "ČR": "cz", "CZECHIA": "cz",
        "SVK": "sk", "SLOVENSKO": "sk", "SLOVAKIA": "sk",
        "CAN": "ca", "KANADA": "ca", "USA": "us", "FIN": "fi", "FINSKO": "fi",
        "SWE": "se", "ŠVÉDSKO": "se", "SUI": "ch", "ŠVÝCARSKO": "ch",
        "GER": "de", "NĚMECKO": "de", "LAT": "lv", "LOTYŠSKO": "lv",
        "NOR": "no", "NORSKO": "no", "DEN": "dk", "DÁNSKO": "dk",
        "AUT": "at", "RAKOUSKO": "at", "FRA": "fr", "FRANCIE": "fr",
        "KAZ": "kz", "KAZACHSTÁN": "kz", "ITA": "it", "ITÁLIE": "it",
        "SLO": "si", "SLOVINSKO": "si", "HUN": "hu", "MAĎARSKO": "hu"
    }
    code = codes.get(team, "un")
    return f"https://flagcdn.com/w80/{code}.png"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=2).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=2).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=2).dropna(how='all')
    
    df_m.columns = [str(c).strip().lower() for c in df_m.columns]
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['status'] = df_m['status'].astype(str).str.strip().str.lower()
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True, errors='coerce')
    
    if not df_b.empty:
        df_b['match_id'] = df_b['match_id'].astype(str)
        df_b['points_earned'] = pd.to_numeric(df_b['points_earned'], errors='coerce').fillna(0)
        
    if not df_u.empty:
        df_u['total_points'] = pd.to_numeric(df_u['total_points'], errors='coerce').fillna(0)
        
    return conn, df_m, df_b, df_u

conn, df_matches, df_bets, df_users = load_data()

# Session State inicializace
if 'user' not in st.session_state: st.session_state.user = None
if 'is_barman' not in st.session_state: st.session_state.is_barman = False
if 'show_barman_login' not in st.session_state: st.session_state.show_barman_login = False

# --- LOGO ---
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="280"></div>', unsafe_allow_html=True)

# --- LOGIKA PŘIHLÁŠENÍ ---
if st.session_state.user is None and not st.session_state.is_barman:
    col_a, col_b = st.columns([1, 1], gap="large")
    
    with col_a:
        st.subheader("📜 Pravidla")
        st.info("🎯 5 bodů za přesný výsledek\n\n🏒 3 body za rozdíl/remízu\n\n🏆 2 body za vítěze")
        
        st.subheader("🏆 Leaderboard")
        if not df_users.empty:
            top_5 = df_users.sort_values('total_points', ascending=False).head(5).copy()
            top_5['total_points'] = top_5['total_points'].astype(int)
            st.table(top_5[['user_name', 'total_points']].rename(columns={'user_name':'Přezdívka', 'total_points':'Body'}))

    with col_b:
        st.subheader("🔑 Vstup do hry")
        with st.form("login_form"):
            u_input = st.text_input("Přezdívka")
            p_input = st.text_input("PIN (4 čísla)", type="password")
            btn = st.form_submit_button("Vstoupit / Registrovat")
            
            if btn:
                if u_input and len(p_input) == 4:
                    # OCHRANA DUPLICIT (case-insensitive)
                    existing_users_lower = [name.lower() for name in df_users['user_name'].astype(str)]
                    
                    if u_input.lower() in existing_users_lower:
                        # Pokud uživatel existuje, zkontrolujeme PIN
                        user_row = df_users[df_users['user_name'].str.lower() == u_input.lower()]
                        if str(user_row['pin'].values[0]) == p_input:
                            st.session_state.user = user_row['user_name'].values[0]
                            st.rerun()
                        else:
                            st.error("Uživatel s tímto jménem již existuje. Pokud jsi to ty, zadej správný PIN.")
                    else:
                        # Nová registrace
                        new_u = pd.DataFrame([{"user_name": u_input, "pin": p_input, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_users, new_u], ignore_index=True))
                        st.session_state.user = u_input
                        st.success("Registrace úspěšná!")
                        st.rerun()

    # --- BARMAN SEKCE ---
    st.write("---")
    if st.button("🔒 Režim Barman (vstup pro obsluhu)"):
        st.session_state.show_barman_login = True
    
    if st.session_state.show_barman_login:
        with st.form("barman_login"):
            admin_pwd = st.text_input("Heslo barmana", type="password")
            if st.form_submit_button("Přihlásit do administrace"):
                if admin_pwd == "hokej2026": # Zde si změň heslo
                    st.session_state.is_barman = True
                    st.rerun()
                else:
                    st.error("Špatné heslo.")

# --- BARMAN DASHBOARD ---
elif st.session_state.is_barman:
    st.header("⚙️ Administrace Barman")
    if st.button("Odhlásit admina"):
        st.session_state.is_barman = False
        st.rerun()
    
    st.write("Tady budeš zadávat výsledky (funkce připravena v load_data)")
    # (Zde můžeš později přidat formulář pro zápis výsledků do Sheets)

# --- HRÁČSKÁ ZÓNA ---
else:
    u_row = df_users[df_users['user_name'] == st.session_state.user]
    points = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    
    st.markdown(f"<h2 style='text-align: center;'>Ahoj {st.session_state.user}! 🏒 | Tvůj stav: {points} bodů</h2>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📝 TIPOVÁNÍ", "📊 ŽEBŘÍČEK", "✅ VÝSLEDKY"])
    
    with t1:
        now = datetime.now()
        open_m = df_matches[(df_matches['status'] == 'budoucí') & (df_matches['internal_datetime'] > (now - timedelta(minutes=20)))]
        
        if open_m.empty:
            st.info("Aktuálně nejsou žádné zápasy k tipování.")
            
        for _, m in open_m.iterrows():
            cid = str(m['match_id'])
            # Hledáme tip (přezdívka musí sedět přesně)
            user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
            has_bet = not user_bet.empty
            
            # COUNTDOWN FORMÁT (D:H:M:S)
            lock_time = m['internal_datetime'] + timedelta(minutes=20)
            td = lock_time - now
            days = td.days
            hours, rem = divmod(td.seconds, 3600)
            minutes, seconds = divmod(rem, 60)
            timer_str = f"{days}d : {hours}h : {minutes}m : {seconds}s"

            # Vizuální oddělení kontejnerem
            st.markdown(f'<div class="match-wrapper">', unsafe_allow_html=True)
            
            card_class = "match-card-bet" if has_bet else "match-card"
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; text-align: center;">
                    <div style="width: 35%;"><img src="{get_flag_url(m['team_a'])}" width="60"><br><b>{m['team_a']}</b></div>
                    <div style="width: 30%; font-size: 1.2em; font-weight: bold;">VS<br><span style="font-size: 0.6em; color: #666;">{m['date']} {m['time']}</span></div>
                    <div style="width: 35%;"><img src="{get_flag_url(m['team_b'])}" width="60"><br><b>{m['team_b']}</b></div>
                </div>
                <p style="text-align: center; margin-top: 15px; font-family: monospace; color: #d32f2f;">
                    ⏳ Sázky končí za: {timer_str}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if has_bet:
                st.markdown(f'<div class="bet-confirmed">✅ Na tento zápas jsi již tipoval/a. Tvůj tip: {int(user_bet.iloc[0]["tip_a"])} : {int(user_bet.iloc[0]["tip_b"])}</div>', unsafe_allow_html=True)
            else:
                with st.expander("➕ Odeslat tip"):
                    with st.form(key=f"f_{cid}"):
                        c1, c2 = st.columns(2)
                        ta = c1.number_input(f"{m['team_a']}", 0, 20, key=f"v1_{cid}")
                        tb = c2.number_input(f"{m['team_b']}", 0, 20, key=f"v2_{cid}")
                        if st.form_submit_button("POTVRDIT TIP"):
                            new_bet = pd.DataFrame([{
                                "timestamp": now.strftime("%Y-%m-%d %H:%M"),
                                "user_name": st.session_state.user,
                                "match_id": cid,
                                "tip_a": int(ta),
                                "tip_b": int(tb),
                                "points_earned": 0
                            }])
                            conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_bets, new_bet], ignore_index=True))
                            st.cache_data.clear()
                            st.success("Tip uložen!")
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        st.subheader("📊 Žebříček borců")
        if not df_users.empty:
            lead = df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
            lead.index += 1
            lead['total_points'] = lead['total_points'].astype(int) # Fix desetin
            st.table(lead.rename(columns={'user_name': 'Přezdívka', 'total_points': 'Celkem bodů'}))

    with t3:
        st.subheader("✅ Konečné výsledky")
        fin = df_matches[df_matches['status'] == 'ukončeno'].copy()
        if not fin.empty:
            fin['Skóre'] = fin.apply(lambda x: f"{int(x['result_a'])} : {int(x['result_b'])}", axis=1)
            st.table(fin[['date', 'team_a', 'Skóre', 'team_b']].rename(columns={'date':'Datum', 'team_a':'Tým A', 'team_b':'Tým B'}))

    if st.button("Odhlásit se"):
        st.session_state.user = None
        st.rerun()
