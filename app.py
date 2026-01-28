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

# --- PŘIPOJENÍ ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- AGRESIVNÍ LIMETKOVÝ DESIGN ---
st.markdown("""
    <style>
    /* Hlavní pozadí a text */
    .stApp { background-color: #ffffff !important; }
    
    /* Vynucení limetkové na formuláře, tlačítka a karty */
    div[data-testid="stForm"], .stButton > button, div[data-testid="stNotification"] {
        background-color: #CCFF00 !important;
        border: 2px solid #000000 !important;
        color: #000000 !important;
    }
    
    /* Inputy */
    input[type="text"], input[type="password"], input[type="number"] {
        background-color: #ffffff !important;
        border: 2px solid #000000 !important;
        color: #000000 !important;
    }

    /* Karty zápasů */
    .match-card {
        background: #CCFF00 !important;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 15px;
        border: 2px solid #000000;
        box-shadow: 5px 5px 0px #000000;
        color: #000000 !important;
    }
    
    .status-badge {
        padding: 5px 10px;
        border-radius: 20px;
        font-weight: 900;
        border: 2px solid #000;
        background: white;
    }

    h1, h2, h3, h4, h5, h6, p, label, span {
        color: #000000 !important;
        font-weight: bold !important;
    }
    
    /* Skrytí postranního panelu */
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCE ---
def get_now():
    return datetime.now(PRG)

def get_flag(team_code):
    codes = {"CZE":"cz","SVK":"sk","CAN":"ca","USA":"us","FIN":"fi","SWE":"se","SUI":"ch","GER":"de","LAT":"lv","NOR":"no","DEN":"dk","AUT":"at","FRA":"fr","KAZ":"kz"}
    c = codes.get(str(team_code).strip().upper(), "")
    if c == "": return "https://cdn-icons-png.flaticon.com/512/3557/3557263.png" # Ikona hokeje
    return f"https://flagcdn.com/w80/{c}.png"

@st.cache_data(ttl=2)
def load_data():
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=0).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True).dt.tz_localize(PRG)
    df_u['total_points'] = pd.to_numeric(df_u['total_points'], errors='coerce').fillna(0).astype(int)
    return df_m, df_b, df_u

df_m, df_b, df_u = load_data()

# --- SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False
if 'reg_mode' not in st.session_state: st.session_state.reg_mode = None

# --- TOKEN LOGIN LOGIKA (MUSÍ BÝT NAHOŘE) ---
token_param = st.query_params.get("token")
if token_param and not st.session_state.user:
    u_match = df_u[df_u['token'].astype(str) == str(token_param)]
    if not u_match.empty:
        row = u_match.iloc[0]
        # Pokud je token v systému, ale nemá jméno -> REGISTRACE
        if pd.isna(row['user_name']) or str(row['user_name']).strip() == "":
            st.session_state.reg_mode = token_param
        else:
            # Automatické přihlášení
            st.session_state.user = row['user_name']
            st.rerun()

# --- UI LOGO ---
st.image(LOGO_URL, width=200)

# --- 1. NEPROLOGOVANÝ UŽIVATEL ---
if not st.session_state.user and not st.session_state.admin:
    
    if st.session_state.reg_mode:
        with st.form("activation"):
            st.subheader("🎉 Aktivuj svůj QR kód")
            new_name = st.text_input("Zvol si přezdívku").strip()
            new_pin = st.text_input("Zvol si 4místný PIN", type="password", max_chars=4).strip()
            if st.form_submit_button("ZAČÍT TIPOVAT"):
                if new_name and len(new_pin) == 4:
                    df_u.loc[df_u['token'].astype(str) == str(st.session_state.reg_mode), ['user_name', 'pin', 'total_points']] = [new_name, new_pin, 0]
                    conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                    st.session_state.user = new_name
                    st.session_state.reg_mode = None
                    st.cache_data.clear()
                    st.rerun()
                else: st.warning("Vyplň jméno a 4místný PIN.")
    
    else:
        t1, t2, t3 = st.tabs(["🔥 DOMŮ", "🔑 VSTUP", "📜 PRAVIDLA"])
        
        with t1:
            st.subheader("Dnešní program")
            dnes = df_m[df_m['date'].astype(str).str.contains(get_now().strftime("%d.%m.%Y"))]
            if dnes.empty: st.info("Dnes se nic nehraje.")
            for _, m in dnes.iterrows():
                st.markdown(f"🏒 **{m['time']}** | {m['team_a']} vs {m['team_b']}")
            st.divider()
            st.subheader("Průběžné pořadí")
            if not df_u.empty:
                lead = df_u[df_u['user_name'] != ""].sort_values('total_points', ascending=False).reset_index(drop=True)
                lead.index += 1
                st.table(lead[['user_name', 'total_points']].rename(columns={'user_name':'Hráč','total_points':'Body'}).head(10))

        with t2:
            with st.form("login"):
                u_in = st.text_input("Přezdívka").strip()
                p_in = st.text_input("PIN", type="password").strip()
                if st.form_submit_button("PŘIHLÁSIT SE"):
                    # Robustnější hledání (očištění od mezer a case-insensitive)
                    match = df_u[df_u['user_name'].str.lower().str.strip() == u_in.lower()]
                    if not match.empty:
                        if str(match.iloc[0]['pin']).strip() == p_in:
                            st.session_state.user = match.iloc[0]['user_name']
                            st.rerun()
                        else: st.error("Chybný PIN.")
                    else: st.error("Uživatel s touto přezdívkou neexistuje.")

            if st.text_input("Admin", type="password") == "hokej2026":
                if st.button("Vstoupit do Adminu"): st.session_state.admin = True; st.rerun()

        with t3:
            if os.path.exists("pravidla.md"):
                with open("pravidla.md", "r", encoding="utf-8") as f: st.markdown(f.read())

# --- 2. HRÁČSKÉ PROSTŘEDÍ ---
elif st.session_state.user:
    u_data = df_u[df_u['user_name'] == st.session_state.user].iloc[0]
    st.markdown(f"### 🏒 Hráč: {st.session_state.user} | 🏆 {int(u_data['total_points'])} b.")
    if st.button("ODHLÁSIT"): 
        st.session_state.user = None
        st.query_params.clear()
        st.rerun()
    
    t_t, t_z, t_p = st.tabs(["🏒 TIPOVÁNÍ", "🏆 POŘADÍ", "📜 PRAVIDLA"])
    
    with t_t:
        now = get_now()
        for _, m in df_m.sort_values('internal_datetime').iterrows():
            lock = m['internal_datetime'] + timedelta(minutes=20)
            is_locked = now > lock
            is_done = str(m['status']).lower() == 'ukončeno'
            
            # Karty
            st.markdown(f"""
                <div class="match-card">
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span style="font-size:0.8rem;">{m['date']} | {m['group']}</span>
                        <span class="status-badge">{"KONEC" if is_done else ("ZAMKNUTO" if is_locked else "TIPUJ!")}</span>
                    </div>
                    <div style="display:flex; align-items:center; text-align:center;">
                        <div style="flex:1;"><img src="{get_flag(m['team_a'])}" width="45"><br><b>{m['team_a']}</b></div>
                        <div style="flex:1;" class="score-display">{"VS" if not is_done else f"{int(m['result_a'])}:{int(m['result_b'])}"}</div>
                        <div style="flex:1;"><img src="{get_flag(m['team_b'])}" width="45"><br><b>{m['team_b']}</b></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            u_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == m['match_id'])]
            
            if not is_locked and not is_done:
                if not u_bet.empty:
                    st.success(f"Tvůj tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])}")
                else:
                    with st.expander("Zadat tip"):
                        with st.form(f"f{m['match_id']}"):
                            c1, c2 = st.columns(2)
                            tA = c1.number_input(f"{m['team_a']}", 0, 20, step=1)
                            tB = c2.number_input(f"{m['team_b']}", 0, 20, step=1)
                            code = st.text_input("KÓD Z TABULE (pro +2 b.)").strip()
                            if st.form_submit_button("POTVRDIT"):
                                is_in_bar = (code.upper() == str(m['bar_code_day']).strip().upper())
                                bonus = 2 if is_in_bar else 0
                                new_bet = pd.DataFrame([{"user_name": st.session_state.user, "match_id": m['match_id'], "tip_a": tA, "tip_b": tB, "points_earned": bonus, "in_bar": is_in_bar}])
                                df_b = pd.concat([df_b, new_bet])
                                df_u.loc[df_u['user_name'] == st.session_state.user, 'total_points'] += bonus
                                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                                st.cache_data.clear(); st.rerun()
            elif not u_bet.empty:
                st.info(f"Tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])} | Zisk: {int(u_bet.iloc[0]['points_earned'])} b.")

    with t_z:
        lead = df_u[df_u['user_name'] != ""].sort_values('total_points', ascending=False).reset_index(drop=True)
        lead.index = [f"{i+1}." for i in lead.index]
        st.table(lead[['user_name', 'total_points']].rename(columns={'user_name':'Hráč','total_points':'Body'}))

    with t_p:
        if os.path.exists("pravidla.md"):
            with open("pravidla.md", "r", encoding="utf-8") as f: st.markdown(f.read())

# --- 3. ADMIN ---
elif st.session_state.admin:
    st.subheader("🛡️ Administrace")
    if st.button("ODHLÁSIT"): st.session_state.admin = False; st.rerun()
    to_eval = df_m[df_m['status'] != 'ukončeno'].sort_values('internal_datetime')
    for _, m in to_eval.iterrows():
        with st.expander(f"{m['team_a']} - {m['team_b']}"):
            rA = st.number_input("Skóre Home", 0, 20, key=f"rA{m['match_id']}")
            rB = st.number_input("Skóre Away", 0, 20, key=f"rB{m['match_id']}")
            if st.button("ULOŽIT VÝSLEDEK", key=f"s{m['match_id']}"):
                df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [rA, rB, 'ukončeno']
                if not df_b.empty:
                    mask = df_b['match_id'] == m['match_id']
                    def calc(row):
                        pts = 0
                        if row['tip_a'] == rA and row['tip_b'] == rB: pts = 5
                        elif (row['tip_a'] - row['tip_b']) == (rA - rB): pts = 3
                        elif (row['tip_a'] > row['tip_b'] and rA > rB) or (row['tip_a'] < row['tip_b'] and rB > rA): pts = 2
                        return row['points_earned'] + pts
                    df_b.loc[mask, 'points_earned'] = df_b[mask].apply(calc, axis=1)
                
                # Přepočet celkem
                sums = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                df_u = df_u.drop(columns=['total_points'], errors='ignore').merge(sums, on='user_name', how='left').fillna(0).rename(columns={'points_earned':'total_points'})
                df_u['total_points'] = df_u['total_points'].astype(int)
                
                conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                st.cache_data.clear(); st.rerun()
