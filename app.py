import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Hokejová Tipovačka 2026", layout="centered")

# --- GRAFIKA (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .stExpander { border: 1px solid #31333f; border-radius: 10px; background-color: #161b22; }
    h1, h2, h3 { color: #ffffff !important; font-family: 'Arial Black', sans-serif; }
    .match-card { padding: 10px; border-bottom: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

# --- FUNKCE PRO VLAJKY ---
def get_flag(team_name):
    flags = {
        "Česko": "🇨🇿", "Slovensko": "🇸🇰", "Kanada": "🇨🇦", "USA": "🇺🇸",
        "Finsko": "🇫🇮", "Švédsko": "🇸🇪", "Švýcarsko": "🇨🇭", "Německo": "🇩🇪",
        "Lotyšsko": "🇱🇻", "Norsko": "🇳🇴", "Dánsko": "🇩🇰", "Rakousko": "🇦🇹",
        "Francie": "🇫🇷", "Kazachstán": "🇰🇿", "Maďarsko": "🇭🇺", "Slovinsko": "🇸🇮"
    }
    return flags.get(team_name, "🏒")

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=2).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=2).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=2).dropna(how='all')
    
    # 1. FIX ČASU: Vytvoříme si výpočetní čas, ale sloupce 'date' a 'time' necháme jako text
    df_m['match_id'] = df_m['match_id'].astype(str)
    
    # Python si spojí datum a čas pro vnitřní logiku (uzavírání sázek)
    # Předpokládá formát v tabulce: Date (12.05.2026) a Time (16:20)
    df_m['internal_datetime'] = pd.to_datetime(
        df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), 
        dayfirst=True, 
        errors='coerce'
    )
    
    df_m['status'] = df_m['status'].astype(str).str.strip().str.lower()
    
    if not df_b.empty:
        df_b['match_id'] = df_b['match_id'].astype(str)
    
    return conn, df_m, df_b, df_u

try:
    conn, df_matches, df_bets, df_users = load_data()
except Exception as e:
    st.error(f"Chyba spojení: {e}")
    st.stop()

if 'user' not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏒 Barová Tipovačka")
    if st.session_state.user:
        st.success(f"Uživatel: **{st.session_state.user}**")
        u_row = df_users[df_users['user_name'] == st.session_state.user]
        pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
        st.metric("Moje body celkem", f"{pts} pts")
        if st.button("Odhlásit se"):
            st.session_state.user = None
            st.rerun()
    else:
        u_in = st.text_input("Přezdívka")
        p_in = st.text_input("PIN (4 čísla)", type="password")
        if st.button("Vstoupit do hry"):
            if u_in and p_in:
                if u_in not in df_users['user_name'].values:
                    new_u = pd.DataFrame([{"user_name": u_in, "pin": p_in, "total_points": 0}])
                    conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_users, new_u], ignore_index=True))
                st.session_state.user = u_in
                st.rerun()

# --- ADMIN (BARMAN) ---
if st.sidebar.checkbox("🔒 Režim Barman"):
    pwd = st.sidebar.text_input("Heslo", type="password")
    if pwd == "hokej2026":
        st.header("⚙️ Vyhodnocení zápasů")
        to_score = df_matches[df_matches['status'] != 'ukončeno'].copy()
        if not to_score.empty:
            for _, m in to_score.iterrows():
                mid = str(m['match_id'])
                with st.container():
                    st.write(f"**{m['team_a']} vs {m['team_b']}** ({m['date']})")
                    c1, c2, c3 = st.columns([1,1,1])
                    res_a = c1.number_input(f"{m['team_a']}", 0, 20, key=f"a_{mid}")
                    res_b = c2.number_input(f"{m['team_b']}", 0, 20, key=f"b_{mid}")
                    if c3.button("Uložit", key=f"s_{mid}"):
                        def calc(ta, tb, ra, rb):
                            if ta == ra and tb == rb: return 5
                            if (ra-rb) == (ta-tb): return 3
                            if (ra>rb and ta>tb) or (ra<rb and ta<tb): return 2
                            return 0
                        if not df_bets.empty:
                            df_bets['points_earned'] = df_bets.apply(
                                lambda x: calc(x['tip_a'], x['tip_b'], res_a, res_b) if x['match_id'] == mid else x['points_earned'], axis=1
                            )
                        df_matches.loc[df_matches['match_id'] == mid, ['result_a', 'result_b', 'status']] = [res_a, res_b, 'ukončeno']
                        # Přepočet celkových bodů
                        nt = df_bets.groupby('user_name')['points_earned'].sum().reset_index()
                        df_users = df_users.drop(columns=['total_points']).merge(nt, on='user_name', how='left').fillna(0)
                        df_users.rename(columns={'points_earned': 'total_points'}, inplace=True)
                        
                        conn.update(spreadsheet=URL, worksheet="Bets", data=df_bets)
                        conn.update(spreadsheet=URL, worksheet="Matches", data=df_matches)
                        conn.update(spreadsheet=URL, worksheet="Users", data=df_users)
                        st.cache_data.clear()
                        st.rerun()
        st.stop()

# --- HLAVNÍ OBSAH ---
if st.session_state.user:
    t1, t2, t3 = st.tabs(["📝 TIPOVAT", "🏆 ŽEBŘÍČEK", "📅 VÝSLEDKY"])
    
    with t1:
        now = datetime.now()
        # Zobrazíme zápasy 'budoucí', které nezačaly před více než 20 minutami
        open_m = df_matches[
            (df_matches['status'] == 'budoucí') & 
            (df_matches['internal_datetime'] > (now - timedelta(minutes=20)))
        ].copy()

        if not open_m.empty:
            for d in open_m['date'].unique():
                with st.expander(f"📅 Zápasy {d}", expanded=True):
                    day_matches = open_m[open_m['date'] == d]
                    for _, m in day_matches.iterrows():
                        cid = str(m['match_id'])
                        user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
                        
                        flag_a = get_flag(m['team_a'])
                        flag_b = get_flag(m['team_b'])
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"### {flag_a} {m['team_a']} vs {m['team_b']} {flag_b}")
                            st.caption(f"Skupina {m['group']} | ⏰ Začátek v {m['time']}")
                        
                        with col2:
                            if not user_bet.empty:
                                st.success(f"Tvůj tip: {int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}")
                            else:
                                if st.button(f"Vsadit", key=f"b_{cid}"):
                                    st.session_state[f"bet_{cid}"] = True
                        
                        if st.session_state.get(f"bet_{cid}") and user_bet.empty:
                            with st.form(key=f"f_{cid}"):
                                ca, cb = st.columns(2)
                                ta = ca.number_input(f"{m['team_a']}", 0, 20, 0)
                                tb = cb.number_input(f"{m['team_b']}", 0, 20, 0)
                                if st.form_submit_button("Potvrdit tip"):
                                    new_b = pd.DataFrame([{
                                        "timestamp": now.strftime("%d.%m. %H:%M"), 
                                        "user_name": st.session_state.user, 
                                        "match_id": cid, 
                                        "tip_a": int(ta), "tip_b": int(tb), 
                                        "points_earned": 0
                                    }])
                                    conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_bets, new_b], ignore_index=True))
                                    st.cache_data.clear()
                                    st.session_state[f"bet_{cid}"] = False
                                    st.rerun()
        else:
            st.info("Momentálně nejsou žádné zápasy k tipování.")

    with t2:
        st.subheader("🏆 Aktuální pořadí v baru")
        lead = df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
        lead.index += 1
        st.table(lead)

    with t3:
        st.subheader("📅 Odehrané zápasy")
        finished = df_matches[df_matches['status'] == 'ukončeno'].copy()
        if not finished.empty:
            # Přidání vlajek i do výsledků
            finished['Zápas'] = finished.apply(lambda x: f"{get_flag(x['team_a'])} {x['team_a']} {int(x['result_a'])}:{int(x['result_b'])} {x['team_b']} {get_flag(x['team_b'])}", axis=1)
            st.write(finished[['date', 'Zápas']].set_index('date'))
        else:
            st.write("Zatím žádné výsledky.")
else:
    st.info("👈 Přihlas se vlevo v menu, abys mohl začít tipovat!")
