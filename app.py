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
    
    /* Centrování loga pro mobil i PC */
    .logo-container { 
        display: flex; 
        justify-content: center; 
        align-items: center;
        padding: 20px 0; 
    }
    
    /* Karty zápasů */
    .match-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border: 1px solid #e9ecef;
    }
    
    /* Zelená karta po tipování */
    .match-card-bet {
        background-color: #f0fff4 !important;
        border: 2px solid #32cd32 !important;
    }
    
    /* Hláška po tipování */
    .bet-header { 
        color: #28a745; 
        font-weight: bold; 
        padding: 10px;
        border-radius: 5px;
        margin-top: -10px;
        margin-bottom: 10px;
    }

    /* Vylepšení vzhledu tlačítka "Odeslat tip" */
    .stExpander summary {
        color: #32cd32 !important;
        font-weight: bold;
        font-size: 1.1em;
    }

    /* Skrytí sidebar menu */
    [data-testid="stSidebar"] { display: none; }
    
    /* Tabulky bez indexů */
    .stTable { width: 100%; }
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
    
    # Oprava internal_datetime
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True, errors='coerce')
    df_m['match_id'] = df_m['match_id'].astype(str)
    
    # OPRAVA CHYBY: Přidáno .str před .lower()
    df_m['status'] = df_m['status'].astype(str).str.strip().str.lower()
    
    return conn, df_m, df_b, df_u

# Načtení dat
try:
    conn, df_matches, df_bets, df_users = load_data()
except Exception as e:
    st.error(f"Chyba při načítání dat: {e}")
    st.stop()

if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False

# --- LOGO (VYCENTROVANÉ) ---
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="250"></div>', unsafe_allow_html=True)

# --- LOGIKA STRÁNEK ---
if st.session_state.user is None:
    # --- LANDING PAGE ---
    col_a, col_b = st.columns([1, 1], gap="large")
    with col_a:
        st.subheader("📜 Pravidla")
        st.info("5 bodů: přesný tip | 3 body: rozdíl/remíza | 2 body: vítěz")
        
        st.subheader("🏆 Aktuální pořadí")
        if not df_users.empty:
            top_5 = df_users.sort_values('total_points', ascending=False).head(5)
            st.table(top_5[['user_name', 'total_points']].rename(columns={'user_name': 'Přezdívka', 'total_points': 'Celkem bodů'}))

    with col_b:
        st.subheader("🔑 Vstup do hry")
        with st.form("login"):
            u_in = st.text_input("Přezdívka")
            p_in = st.text_input("PIN (4 čísla)", type="password")
            if st.form_submit_button("Přihlásit / Registrovat"):
                if u_in and len(p_in) == 4:
                    if u_in not in df_users['user_name'].values:
                        new_u = pd.DataFrame([{"user_name": u_in, "pin": p_in, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_users, new_u], ignore_index=True))
                    st.session_state.user = u_in
                    st.rerun()

    st.divider()
    st.subheader("📅 Nejbližší zápasy")
    # Filtr pro dnešní a budoucí zápasy (seřazeno podle času)
    now = datetime.now()
    upcoming = df_matches[df_matches['internal_datetime'] >= now.replace(hour=0, minute=0)].sort_values('internal_datetime').head(5)
    for _, m in upcoming.iterrows():
        st.write(f"🏒 **{m['team_a']} vs {m['team_b']}** | {m['date']} v {m['time']}")
    
    # Skryté tlačítko pro Barmana
    st.write("---")
    if st.button("🔒 Režim Barman"):
        st.info("Pro režim barman se přihlas jako admin (funkce v přípravě nebo přes sidebar)")

else:
    # --- PŘIHLÁŠENÝ UŽIVATEL ---
    u_row = df_users[df_users['user_name'] == st.session_state.user]
    u_pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    
    st.markdown(f"<h3 style='text-align: center;'>Ahoj {st.session_state.user}! 👋 | Tvůj stav: {u_pts} bodů</h3>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📝 TIPOVÁNÍ", "📊 ŽEBŘÍČEK", "✅ VÝSLEDKY"])
    
    with t1:
        now = datetime.now()
        # Zápasy, které ještě neskončily (start + 20 min)
        open_m = df_matches[(df_matches['status'] == 'budoucí') & (df_matches['internal_datetime'] > (now - timedelta(minutes=20)))]
        
        if open_m.empty:
            st.info("Momentálně nejsou žádné zápasy k tipování.")
        
        for _, m in open_m.iterrows():
            cid = str(m['match_id'])
            user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
            is_bet = not user_bet.empty
            
            # Tie-out výpočet
            lock_time = m['internal_datetime'] + timedelta(minutes=20)
            diff = lock_time - now
            minutes_left = int(diff.total_seconds() // 60)
            countdown_text = f"Sázky končí za: {minutes_left} min" if minutes_left > 0 else "Sázky končí každou chvíli!"

            # Karta zápasu
            card_style = "match-card-bet" if is_bet else "match-card"
            st.markdown(f"""
            <div class="{card_style}">
                <div style="display: flex; justify-content: space-between; align-items: center; text-align: center;">
                    <div style="width: 40%;"><img src="{get_flag_url(m['team_a'])}" width="60"><br><b>{m['team_a']}</b></div>
                    <div style="width: 20%; font-size: 1.2em;">VS</div>
                    <div style="width: 40%;"><img src="{get_flag_url(m['team_b'])}" width="60"><br><b>{m['team_b']}</b></div>
                </div>
                <p style="text-align: center; color: #6c757d; margin-top: 10px;">
                    📅 {m['date']} | ⏰ {m['time']} | ⏳ {countdown_text}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if is_bet:
                st.markdown(f"<div class='bet-header'>✅ Na tento zápas jsi již tipoval/a. Tvůj tip: {int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}</div>", unsafe_allow_html=True)
            else:
                with st.expander("🟢 Odeslat tip"):
                    with st.form(key=f"form_{cid}"):
                        col_a, col_b = st.columns(2)
                        ta = col_a.number_input(f"{m['team_a']}", 0, 20, key=f"ta_{cid}")
                        tb = col_b.number_input(f"{m['team_b']}", 0, 20, key=f"tb_{cid}")
                        if st.form_submit_button("POTVRDIT TIP"):
                            new_row = pd.DataFrame([{"timestamp": now.strftime("%H:%M"), "user_name": st.session_state.user, "match_id": cid, "tip_a": int(ta), "tip_b": int(tb), "points_earned": 0}])
                            conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_bets, new_row]))
                            st.cache_data.clear()
                            st.rerun()

    with t2:
        st.subheader("🏆 Průběžné pořadí")
        if not df_users.empty:
            lead = df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
            lead.index += 1
            st.table(lead.rename(columns={'user_name': 'Přezdívka', 'total_points': 'Celkem bodů'}))

    with t3:
        st.subheader("✅ Odehrané zápasy")
        fin = df_matches[df_matches['status'] == 'ukončeno'].copy()
        if not fin.empty:
            # Skóre bez desetin
            fin['Výsledek'] = fin.apply(lambda x: f"{int(x['result_a'])} : {int(x['result_b'])}", axis=1)
            st.table(fin[['date', 'team_a', 'Výsledek', 'team_b']].rename(columns={'date': 'Datum', 'team_a': 'Tým A', 'team_b': 'Tým B'}))
        else:
            st.write("Zatím nejsou žádné výsledky k zobrazení.")

    if st.button("Odhlásit se"):
        st.session_state.user = None
        st.rerun()
