import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURÁCIA ---
st.set_page_config(page_title="Infi Tipovačka 2026", layout="centered")

# --- ODKAZ NA LOGO (RAW) ---
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

# --- GRAFIKA (CSS) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e1117; }}
    .stButton>button {{ 
        width: 100%; 
        border-radius: 8px; 
        font-weight: bold; 
        background-color: #e63946; /* Červená ladiaca k logu */
        color: white; 
        border: none;
    }}
    .stExpander {{ border: 1px solid #31333f; border-radius: 10px; background-color: #161b22; }}
    h1, h2, h3 {{ color: #ffffff !important; }}
    /* Úprava tabuľky žebříčku */
    [data-testid="stTable"] {{ background-color: #161b22; border-radius: 10px; }}
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

# --- FUNKCIA PRE OBRÁZKOVÉ VLAJKY ---
def get_flag_url(team_name):
    team = str(team_name).strip().upper()
    codes = {{
        "CZE": "cz", "ČESKO": "cz", "SVK": "sk", "SLOVENSKO": "sk",
        "CAN": "ca", "KANADA": "ca", "USA": "us", "FIN": "fi", 
        "FINSKO": "fi", "SWE": "se", "ŠVÉDSKO": "se", "SUI": "ch", 
        "ŠVÝCARSKO": "ch", "GER": "de", "NĚMECKO": "de", "LAT": "lv", 
        "LOTYŠSKO": "lv", "NOR": "no", "NORSKO": "no", "DEN": "dk", 
        "DÁNSKO": "dk", "AUT": "at", "RAKOUSKO": "at", "FRA": "fr", 
        "FRANCIE": "fr", "KAZ": "kz", "KAZACHSTÁN": "kz", "ITA": "it", 
        "ITÁLIE": "it", "SLO": "si", "SLOVINSKO": "si", "HUN": "hu"
    }}
    code = codes.get(team, "un")
    return f"https://flagcdn.com/w40/{{code}}.png"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=2).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=2).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=2).dropna(how='all')
    df_m.columns = [str(c).strip().lower() for c in df_m.columns]
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True, errors='coerce')
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['status'] = df_m['status'].astype(str).str.strip().str.lower()
    return conn, df_m, df_b, df_u

try:
    conn, df_matches, df_bets, df_users = load_data()
except Exception as e:
    st.error(f"Chyba pripojenia: {{e}}"); st.stop()

if 'user' not in st.session_state: st.session_state.user = None

# --- SIDEBAR (S LOGOM) ---
with st.sidebar:
    st.image(LOGO_URL, use_container_width=True)
    st.title("Infi Tipovačka")
    st.divider()
    
    if st.session_state.user:
        st.success(f"Hráč: **{{st.session_state.user}}**")
        u_row = df_users[df_users['user_name'] == st.session_state.user]
        pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
        st.metric("Tvoje body", f"{{pts}} pts")
        if st.button("Odhlásiť sa"):
            st.session_state.user = None
            st.rerun()
    else:
        u_in = st.text_input("Přezdívka")
        p_in = st.text_input("PIN (4 čísla)", type="password")
        if st.button("Vstúpiť do hry"):
            if u_in and p_in:
                if u_in not in df_users['user_name'].values:
                    new_u = pd.DataFrame([{{ "user_name": u_in, "pin": p_in, "total_points": 0 }}])
                    conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_users, new_u], ignore_index=True))
                st.session_state.user = u_in; st.rerun()

# --- HLAVNÝ OBSAH ---
if st.session_state.user:
    t1, t2, t3 = st.tabs(["📝 TIPOVANIE", "🏆 REBRÍČEK", "📅 VÝSLEDKY"])
    
    with t1:
        now = datetime.now()
        open_m = df_matches[(df_matches['status'] == 'budoucí') & (df_matches['internal_datetime'] > (now - timedelta(minutes=20)))]
        if not open_m.empty:
            for d in open_m['date'].unique():
                with st.expander(f"📅 Zápasy {{d}}", expanded=True):
                    day_m = open_m[open_m['date'] == d]
                    for _, m in day_m.iterrows():
                        cid = str(m['match_id'])
                        user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
                        
                        col1, col2, col3, col4, col5 = st.columns([1, 3, 1, 3, 1])
                        col1.image(get_flag_url(m['team_a']), width=35)
                        col2.write(f"**{{m['team_a']}}**")
                        col3.write("vs")
                        col4.write(f"**{{m['team_b']}}**")
                        col5.image(get_flag_url(m['team_b']), width=35)
                        
                        st.caption(f"⏰ {{m['time']}} | Skupina {{m['group']}}")
                        
                        if not user_bet.empty:
                            st.info(f"Tvoj tip: {{int(user_bet.iloc[0]['tip_a'])}}:{{int(user_bet.iloc[0]['tip_b'])}}")
                        else:
                            if st.button(f"Tipnúť", key=f"b_{{cid}}"):
                                st.session_state[f"bet_{{cid}}"] = True
                        
                        if st.session_state.get(f"bet_{{cid}}") and user_bet.empty:
                            with st.form(key=f"f_{{cid}}"):
                                c1, c2 = st.columns(2)
                                ta = c1.number_input(f"{{m['team_a']}}", 0, 20)
                                tb = c2.number_input(f"{{m['team_b']}}", 0, 20)
                                if st.form_submit_button("Potvrdiť"):
                                    new_b = pd.DataFrame([{{ "timestamp": now.strftime("%d.%m. %H:%M"), "user_name": st.session_state.user, "match_id": cid, "tip_a": int(ta), "tip_b": int(tb), "points_earned": 0 }}])
                                    conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_bets, new_b], ignore_index=True))
                                    st.cache_data.clear(); st.session_state[f"bet_{{cid}}"] = False; st.rerun()
                        st.divider()
        else: st.info("Momentálne nie sú žiadne zápasy na tipovanie.")

    with t2:
        st.subheader("🏆 Aktuálne poradie")
        lead = df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
        lead.index += 1; st.table(lead)

    with t3:
        st.subheader("📅 Posledné výsledky")
        fin = df_matches[df_matches['status'] == 'ukončeno'].copy()
        if not fin.empty:
            for _, r in fin.iterrows():
                c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 2, 1])
                c1.image(get_flag_url(r['team_a']), width=30)
                c2.write(r['team_a'])
                c3.write(f"**{{int(r['result_a'])}} : {{int(r['result_b'])}}**")
                c4.write(r['team_b'])
                c5.image(get_flag_url(r['team_b']), width=30)
                st.divider()
        else: st.write("Zatiaľ žiadne výsledky.")
else:
    st.info("👈 Pre tipovanie sa prihlás v bočnom paneli.")
