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

# --- SEXY LIMETKOVÝ DESIGN ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    
    /* Limetkové prvky */
    div.stButton > button, div.stDownloadButton > button, .stForm div[data-testid="stMarkdownContainer"] button {
        background-color: #CCFF00 !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        font-weight: bold !important;
        border-radius: 8px;
    }
    
    /* Vstupy a tabulky */
    input, select, textarea, [data-baseweb="select"] {
        background-color: #CCFF00 !important;
        color: #000000 !important;
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
    
    .score-display { font-size: 1.8rem; font-weight: 900; color: #000; margin: 0 15px; }
    .team-box { text-align: center; flex: 1; }
    .team-name { font-weight: bold; display: block; margin-top: 5px; }
    
    /* Tabulky */
    [data-testid="stTable"] {
        background-color: #CCFF00 !important;
        border: 2px solid #000 !important;
    }
    
    h1, h2, h3, p, span, label { color: #000000 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCE ---
def get_now():
    return datetime.now(PRG)

def get_flag(team_code):
    codes = {"CZE":"cz","SVK":"sk","CAN":"ca","USA":"us","FIN":"fi","SWE":"se","SUI":"ch","GER":"de","LAT":"lv","NOR":"no","DEN":"dk","AUT":"at","FRA":"fr","KAZ":"kz"}
    c = codes.get(str(team_code).strip().upper(), "un")
    return f"https://flagcdn.com/w80/{c}.png"

@st.cache_data(ttl=5)
def load_data():
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=0).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True).dt.tz_localize(PRG)
    return df_m, df_b, df_u

def show_rules():
    if os.path.exists("pravidla.md"):
        with open("pravidla.md", "r", encoding="utf-8") as f: st.markdown(f.read())
    else: st.info("Pravidla budou brzy doplněna.")

df_m, df_b, df_u = load_data()

# --- SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False

# --- HOME / LOGIN ---
if not st.session_state.user and not st.session_state.admin:
    st.image(LOGO_URL, width=200)
    t1, t2, t3 = st.tabs(["🔥 AKTUÁLNĚ", "🔑 VSTUP", "📜 PRAVIDLA"])
    
    with t1:
        st.subheader("Dnešní pecky")
        dnes = df_m[df_m['date'] == get_now().strftime("%d.%m.%Y")]
        for _, m in dnes.iterrows():
            st.markdown(f"🏒 **{m['time']}** | {m['team_a']} vs {m['team_b']}")
        st.divider()
        st.subheader("Žebříček")
        if not df_u.empty:
            top = df_u[df_u['user_name'] != ""].sort_values('total_points', ascending=False).reset_index(drop=True)
            top.index += 1
            st.table(top[['user_name', 'total_points']].rename(columns={'user_name':'Hráč', 'total_points':'Body'}).head(10))

    with t2:
        with st.form("login"):
            u = st.text_input("Přezdívka").strip()
            p = st.text_input("PIN", type="password").strip()
            if st.form_submit_button("VSTOUPIT"):
                match = df_u[df_u['user_name'].str.lower() == u.lower()]
                if not match.empty and str(match.iloc[0]['pin']) == p:
                    st.session_state.user = match.iloc[0]['user_name']
                    st.rerun()
                else: st.error("Špatné jméno nebo PIN!")
        if st.text_input("Admin", type="password") == "hokej2026":
            if st.button("Admin Vstup"): st.session_state.admin = True; st.rerun()

    with t3: show_rules()

# --- HRÁČSKÉ PROSTŘEDÍ ---
elif st.session_state.user:
    u_row = df_u[df_u['user_name'] == st.session_state.user].iloc[0]
    st.markdown(f"### 😎 {st.session_state.user} | 🏆 {u_row['total_points']} bodů")
    if st.button("ODHLÁSIT"): st.session_state.user = None; st.rerun()
    
    tab_t, tab_z, tab_p = st.tabs(["🏒 TIPOVÁNÍ", "🏆 POŘADÍ", "📜 PRAVIDLA"])
    
    with tab_t:
        now = get_now()
        for _, m in df_m.sort_values('internal_datetime').iterrows():
            lock_time = m['internal_datetime'] + timedelta(minutes=20)
            is_locked = now > lock_time
            is_done = m['status'] == 'ukončeno'
            
            # Výpočet času
            if is_done: status, b_cls = "UKONČENO", "badge-locked"
            elif is_locked: status, b_cls = "ZAMKNUTO", "badge-locked"
            else:
                diff = lock_time - now
                mins = int(diff.total_seconds() // 60)
                status = f"TIPUJ! (zbývá {mins} min)"
                b_cls = "badge-open"

            st.markdown(f"""
                <div class="match-card">
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                        <span style="font-size:0.8rem;">{m['date']} | {m['group']}</span>
                        <span class="status-badge {b_cls}">{status}</span>
                    </div>
                    <div style="display:flex; align-items:center;">
                        <div class="team-box"><img src="{get_flag(m['team_a'])}" width="40"><br><span class="team-name">{m['team_a']}</span></div>
                        <div class="score-display">{"VS" if not is_done else f"{int(m['result_a'])}:{int(m['result_b'])}"}</div>
                        <div class="team-box"><img src="{get_flag(m['team_b'])}" width="40"><br><span class="team-name">{m['team_b']}</span></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            u_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == m['match_id'])]
            
            if not is_locked:
                if not u_bet.empty:
                    st.success(f"Tvůj tip: {int(u_bet.iloc[0]['tip_a'])}:{int(u_bet.iloc[0]['tip_b'])} {'(BAR BONUS +2 ✅)' if u_bet.iloc[0]['in_bar'] else ''}")
                else:
                    with st.expander("ODESLAT TIP"):
                        with st.form(f"f_{m['match_id']}"):
                            c1, c2 = st.columns(2)
                            tA = c1.number_input(f"Góly {m['team_a']}", 0, 20)
                            tB = c2.number_input(f"Góly {m['team_b']}", 0, 20)
                            code = st.text_input("KÓD Z TABULE (pro +2 body)").strip()
                            if st.form_submit_button("POTVRDIT TIP"):
                                is_in_bar = (code.upper() == str(m['bar_code_day']).upper())
                                bonus_pts = 2 if is_in_bar else 0
                                
                                # Uložení sázky
                                new_b = pd.DataFrame([{"user_name": st.session_state.user, "match_id": m['match_id'], "tip_a": tA, "tip_b": tB, "points_earned": bonus_pts, "in_bar": is_in_bar}])
                                df_b = pd.concat([df_b, new_b])
                                
                                # OKAMŽITÉ PŘIČTENÍ BODŮ UŽIVATELI
                                df_u.loc[df_u['user_name'] == st.session_state.user, 'total_points'] += bonus_pts
                                
                                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                                st.cache_data.clear(); st.rerun()

    with tab_z:
        res = df_u[df_u['user_name'] != ""].sort_values('total_points', ascending=False).reset_index(drop=True)
        res.index = [f"{i+1}." for i in res.index]
        st.table(res[['user_name', 'total_points']].rename(columns={'user_name':'Hráč', 'total_points':'Body'}))
    
    with tab_p: show_rules()

# --- ADMIN PROSTŘEDÍ ---
elif st.session_state.admin:
    st.title("🛡️ Admin Rozhraní")
    if st.button("ZPĚT"): st.session_state.admin = False; st.rerun()
    
    eval_m = df_m[df_m['status'] != 'ukončeno']
    for _, m in eval_m.iterrows():
        with st.expander(f"Zapsat výsledek: {m['team_a']} vs {m['team_b']}"):
            resA = st.number_input("Skóre A", 0, 20, key=f"a_{m['match_id']}")
            resB = st.number_input("Skóre B", 0, 20, key=f"b_{m['match_id']}")
            if st.button("UZAVŘÍT ZÁPAS", key=f"btn_{m['match_id']}"):
                df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [resA, resB, 'ukončeno']
                
                # Výpočet hokejových bodů (bonus už mají)
                if not df_b.empty:
                    mask = df_b['match_id'] == m['match_id']
                    def calc_hokej(row):
                        pts = 0
                        if row['tip_a'] == resA and row['tip_b'] == resB: pts = 5
                        elif (row['tip_a'] - row['tip_b']) == (resA - resB): pts = 3
                        elif (row['tip_a'] > row['tip_b'] and resA > resB) or (row['tip_a'] < row['tip_b'] and resA < resB): pts = 2
                        return row['points_earned'] + pts # Přičteme k už existujícím (bonusovým) bodům
                    
                    df_b.loc[mask, 'points_earned'] = df_b[mask].apply(calc_hokej, axis=1)
                
                # Přepočet všech uživatelů
                sums = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                df_u = df_u.drop(columns=['total_points'], errors='ignore').merge(sums, on='user_name', how='left').fillna(0).rename(columns={'points_earned':'total_points'})
                
                conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                st.cache_data.clear(); st.rerun()
