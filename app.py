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

# --- DESIGN ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    div.stButton > button {
        background-color: #CCFF00 !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        font-weight: bold !important;
        width: 100%;
    }
    .match-card {
        background: #ffffff;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 15px;
        border: 2px solid #000000;
        box-shadow: 4px 4px 0px #CCFF00;
    }
    .status-badge {
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 900;
        border: 1px solid #000;
    }
    .badge-open { background-color: #CCFF00; color: #000; }
    .badge-locked { background-color: #ff4b4b; color: #fff; }
    .score-display { font-size: 1.8rem; font-weight: 900; color: #000; }
    h1, h2, h3, p, span, label { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCE ---
def get_now():
    return datetime.now(PRG)

def get_flag(team_code):
    # Mapování s ošetřením mezer a velikosti písma
    codes = {
        "CZE": "cz", "SVK": "sk", "CAN": "ca", "USA": "us", 
        "FIN": "fi", "SWE": "se", "SUI": "ch", "GER": "de", 
        "LAT": "lv", "NOR": "no", "DEN": "dk", "AUT": "at", 
        "FRA": "fr", "KAZ": "kz", "GBR": "gb", "POL": "pl"
    }
    clean_code = str(team_code).strip().upper()
    c = codes.get(clean_code, "un")
    return f"https://flagcdn.com/w80/{c}.png"

@st.cache_data(ttl=2)
def load_data():
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=0).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    
    df_m['match_id'] = df_m['match_id'].astype(str)
    # Převod na datetime s ošetřením chyb
    df_m['internal_datetime'] = pd.to_datetime(
        df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), 
        dayfirst=True
    ).dt.tz_localize(PRG)
    
    # Zaokrouhlení bodů v Users hned při načtení
    df_u['total_points'] = pd.to_numeric(df_u['total_points'], errors='coerce').fillna(0).astype(int)
    return df_m, df_b, df_u

def show_rules():
    if os.path.exists("pravidla.md"):
        with open("pravidla.md", "r", encoding="utf-8") as f: st.markdown(f.read())
    else: st.info("Pravidla budou brzy doplněna v souboru pravidla.md")

df_m, df_b, df_u = load_data()

# --- LOGIN LOGIKA ---
if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False

# --- HOME / LOGIN ---
if not st.session_state.user and not st.session_state.admin:
    st.image(LOGO_URL, width=200)
    t1, t2, t3 = st.tabs(["🔥 AKTUÁLNĚ", "🔑 VSTUP", "📜 PRAVIDLA"])
    
    with t1:
        st.subheader("Dnešní program")
        dnes_str = get_now().strftime("%d.%m.%Y")
        dnes = df_m[df_m['date'].astype(str).str.contains(dnes_str)]
        if dnes.empty: st.write("Dnes se nic nehraje.")
        for _, m in dnes.iterrows():
            st.markdown(f"🏒 **{m['time']}** | {m['team_a']} vs {m['team_b']}")
        
        st.divider()
        st.subheader("Žebříček TOP 10")
        if not df_u.empty:
            top = df_u[df_u['user_name'] != ""].sort_values('total_points', ascending=False).reset_index(drop=True)
            top.index += 1
            top_display = top[['user_name', 'total_points']].rename(columns={'user_name':'Hráč', 'total_points':'Body'}).head(10)
            st.table(top_display)

    with t2:
        with st.form("login_form"):
            u_input = st.text_input("Přezdívka (case-insensitive)").strip()
            p_input = st.text_input("PIN", type="password").strip()
            if st.form_submit_button("VSTOUPIT"):
                # Sjednocení na malá písmena pro neprůstřelný login
                match = df_u[df_u['user_name'].str.lower().str.strip() == u_input.lower()]
                if not match.empty:
                    stored_pin = str(match.iloc[0]['pin']).strip()
                    if stored_pin == p_input:
                        st.session_state.user = match.iloc[0]['user_name']
                        st.rerun()
                    else: st.error("Chybný PIN.")
                else: st.error("Uživatel nenalezen.")
        
        adm_pass = st.text_input("Admin vstup", type="password")
        if adm_pass == "hokej2026":
            if st.button("Otevřít Admin Panel"): st.session_state.admin = True; st.rerun()

    with t3: show_rules()

# --- HRÁČSKÁ ZÓNA ---
elif st.session_state.user:
    # Aktuální data uživatele
    curr_u = df_u[df_u['user_name'] == st.session_state.user].iloc[0]
    st.markdown(f"### 😎 {st.session_state.user} | 🏆 {int(curr_u['total_points'])} bodů")
    if st.button("ODHLÁSIT"): st.session_state.user = None; st.rerun()
    
    tab_t, tab_z, tab_p = st.tabs(["🏒 TIPOVÁNÍ", "🏆 POŘADÍ", "📜 PRAVIDLA"])
    
    with tab_t:
        now = get_now()
        for _, m in df_m.sort_values('internal_datetime').iterrows():
            lock_time = m['internal_datetime'] + timedelta(minutes=20)
            is_locked = now > lock_time
            is_done = str(m['status']).lower() == 'ukončeno'
            
            # Status badge logika
            if is_done: status, b_cls = "KONEC", "badge-locked"
            elif is_locked: status, b_cls = "ZAMKNUTO", "badge-locked"
            else:
                diff = lock_time - now
                mins = int(diff.total_seconds() // 60)
                status = f"TIPUJ! ({mins} min)"
                b_cls = "badge-open"

            st.markdown(f"""
                <div class="match-card">
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span style="font-size:0.75rem;">{m['date']} | {m['group']}</span>
                        <span class="status-badge {b_cls}">{status}</span>
                    </div>
                    <div style="display:flex; align-items:center; text-align:center;">
                        <div style="flex:1;"><img src="{get_flag(m['team_a'])}" width="45"><br><b>{m['team_a']}</b></div>
                        <div style="flex:1;" class="score-display">{"VS" if not is_done else f"{int(m['result_a'])}:{int(m['result_b'])}"}</div>
                        <div style="flex:1;"><img src="{get_flag(m['team_b'])}" width="45"><br><b>{m['team_b']}</b></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            u_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == m['match_id'])]
            
            # ZOBRAZENÍ TIPU NEBO FORMULÁŘE
            if not is_locked and not is_done:
                if not u_bet.empty:
                    st.success(f"Tvůj tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])} {'(BAR BONUS +2 ✅)' if u_bet.iloc[0]['in_bar'] else ''}")
                else:
                    with st.expander("ZADAT TIP"):
                        with st.form(f"form_{m['match_id']}"):
                            c1, c2 = st.columns(2)
                            tA = c1.number_input(f"{m['team_a']}", 0, 20, step=1)
                            tB = c2.number_input(f"{m['team_b']}", 0, 20, step=1)
                            code = st.text_input("KÓD Z TABULE").strip()
                            if st.form_submit_button("ODESLAT"):
                                is_in_bar = (code.upper() == str(m['bar_code_day']).strip().upper())
                                bonus = 2 if is_in_bar else 0
                                
                                new_bet = pd.DataFrame([{"user_name": st.session_state.user, "match_id": m['match_id'], "tip_a": tA, "tip_b": tB, "points_earned": bonus, "in_bar": is_in_bar}])
                                df_b = pd.concat([df_b, new_bet])
                                
                                # Okamžitá aktualizace bodů v paměti a v tabulce
                                df_u.loc[df_u['user_name'] == st.session_state.user, 'total_points'] += bonus
                                
                                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                                st.cache_data.clear()
                                st.rerun()
            else:
                if not u_bet.empty:
                    st.info(f"Tvůj tip byl: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])} | Zisk: {int(u_bet.iloc[0]['points_earned'])} b.")
                else:
                    st.warning("Tento zápas jsi netipoval(a) a už je uzavřen.")

    with tab_z:
        # Pořadí s tečkou a bez desetinných míst
        ranking = df_u[df_u['user_name'] != ""].sort_values('total_points', ascending=False).reset_index(drop=True)
        ranking.index = [f"{i+1}." for i in ranking.index]
        st.table(ranking[['user_name', 'total_points']].rename(columns={'user_name':'Hráč', 'total_points':'Body'}))
    
    with tab_p: show_rules()

# --- ADMIN SEKCE ---
elif st.session_state.admin:
    st.subheader("🛡️ Admin Vyhodnocení")
    if st.button("ZPĚT"): st.session_state.admin = False; st.rerun()
    
    eval_list = df_m[df_m['status'] != 'ukončeno'].sort_values('internal_datetime')
    for _, m in eval_list.iterrows():
        with st.expander(f"Zapsat skóre: {m['team_a']} - {m['team_b']}"):
            resA = st.number_input("Skóre Home", 0, 20, key=f"resA_{m['match_id']}")
            resB = st.number_input("Skóre Away", 0, 20, key=f"resB_{m['match_id']}")
            if st.button("POTVRDIT VÝSLEDEK", key=f"save_{m['match_id']}"):
                df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [resA, resB, 'ukončeno']
                
                if not df_b.empty:
                    m_mask = df_b['match_id'] == m['match_id']
                    def calculate_final(row):
                        pts = 0
                        if row['tip_a'] == resA and row['tip_b'] == resB: pts = 5
                        elif (row['tip_a'] - row['tip_b']) == (resA - resB): pts = 3
                        elif (row['tip_a'] > row['tip_b'] and resA > resB) or (row['tip_a'] < row['tip_b'] and resB > resA): pts = 2
                        return row['points_earned'] + pts # Bonus už tam mají
                    
                    df_b.loc[m_mask, 'points_earned'] = df_b[m_mask].apply(calculate_final, axis=1)
                
                # Celkový přepočet Users
                all_sums = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                df_u = df_u.drop(columns=['total_points'], errors='ignore').merge(all_sums, on='user_name', how='left').fillna(0)
                df_u.rename(columns={'points_earned':'total_points'}, inplace=True)
                df_u['total_points'] = df_u['total_points'].astype(int)
                
                conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                st.cache_data.clear()
                st.rerun()
