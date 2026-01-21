import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Hokejová Tipovačka 2026", layout="centered")

# --- CSS PRO GRAFIKU ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
    }
    .stExpander {
        border: 1px solid #31333f;
        border-radius: 10px;
    }
    h1, h2, h3 {
        color: #f0f2f6 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=10)
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=5)
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=10)
    
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['start_time'] = pd.to_datetime(df_m['start_time'], dayfirst=True, errors='coerce')
    df_m = df_m.sort_values(by='start_time')
    
    if not df_b.empty:
        df_b['match_id'] = df_b['match_id'].astype(str)
    
    return conn, df_m, df_b, df_u

try:
    conn, df_matches, df_bets, df_users = load_data()
except Exception as e:
    st.error(f"Chyba databáze: {e}")
    st.stop()

if 'user' not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏒 Barová Tipovačka")
    if st.session_state.user:
        st.success(f"U stolu: **{st.session_state.user}**")
        # Zobrazení bodů uživatele přímo v sidebaru
        u_pts = df_users[df_users['user_name'] == st.session_state.user]['total_points'].values
        pts = int(u_pts[0]) if len(u_pts) > 0 else 0
        st.metric("Tvoje body", pts)
        
        if st.sidebar.button("Odhlásit se"):
            st.session_state.user = None
            st.rerun()
    else:
        u_in = st.text_input("Jméno / Přezdívka")
        p_in = st.text_input("PIN (4 čísla)", type="password")
        if st.button("Vstoupit do hry"):
            if u_in and len(p_in) == 4:
                if u_in not in df_users['user_name'].values:
                    new_u = pd.DataFrame([{"user_name": u_in, "pin": p_in, "total_points": 0}])
                    up_u = pd.concat([df_users, new_u], ignore_index=True)
                    conn.update(spreadsheet=URL, worksheet="Users", data=up_u)
                    st.cache_data.clear()
                st.session_state.user = u_in
                st.rerun()

# --- ADMIN SEKCE ---
if st.sidebar.checkbox("🔒 Režim Barman"):
    pwd = st.sidebar.text_input("Heslo", type="password")
    if pwd == "hokej2026":
        st.header("⚙️ Admin - Vyhodnocení")
        to_score = df_matches[df_matches['status'] != 'ukončeno'].copy()
        
        if not to_score.empty:
            to_score['date_only'] = to_score['start_time'].dt.strftime('%d.%m.%Y')
            for d in to_score['date_only'].unique():
                with st.expander(f"📅 Zápasy {d}", expanded=True):
                    day_m = to_score[to_score['date_only'] == d]
                    for _, m in day_m.iterrows():
                        mid = str(m['match_id'])
                        st.write(f"**{m['team_a']} vs {m['team_b']}** ({m['group']})")
                        c1, c2, c3 = st.columns([1,1,1])
                        res_a = c1.number_input(f"Skóre {m['team_a']}", 0, 20, 0, key=f"adm_a_{mid}")
                        res_b = c2.number_input(f"Skóre {m['team_b']}", 0, 20, 0, key=f"adm_b_{mid}")
                        
                        if c3.button("Uložit 💾", key=f"save_{mid}"):
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
                            nt = df_bets.groupby('user_name')['points_earned'].sum().reset_index()
                            df_users = df_users.drop(columns=['total_points']).merge(nt, on='user_name', how='left').fillna(0)
                            df_users.rename(columns={'points_earned': 'total_points'}, inplace=True)
                            
                            conn.update(spreadsheet=URL, worksheet="Bets", data=df_bets)
                            conn.update(spreadsheet=URL, worksheet="Matches", data=df_matches)
                            conn.update(spreadsheet=URL, worksheet="Users", data=df_users)
                            st.cache_data.clear()
                            st.success("Hotovo!")
                            st.rerun()
        else: st.info("Vše vyhodnoceno.")
        st.stop()

# --- HRÁČI ---
if st.session_state.user:
    st.title("🏒 Hokejová Tipovačka 2026")
    t1, t2, t3 = st.tabs(["📝 VSADIT SI", "🏆 ŽEBŘÍČEK", "📅 VÝSLEDKY"])
    
    with t1:
        cutoff = datetime.now() - timedelta(minutes=20)
        open_m = df_matches[(df_matches['status'] == 'budoucí') & (df_matches['start_time'] > cutoff)].copy()
        
        if not open_m.empty:
            open_m['date_only'] = open_m['start_time'].dt.strftime('%d.%m.%Y')
            for d in open_m['date_only'].unique():
                with st.expander(f"📅 Zápasy {d}", expanded=True):
                    day_matches = open_m[open_m['date_only'] == d]
                    for _, m in day_matches.iterrows():
                        cid = str(m['match_id'])
                        user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"**{m['team_a']} vs {m['team_b']}**")
                            st.caption(f"Skupina {m['group']} | Začátek: {m['start_time'].strftime('%H:%M')}")
                        
                        with col2:
                            if not user_bet.empty:
                                st.success(f"Tvůj tip: {int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}")
                            else:
                                if st.button(f"Vsadit na zápas", key=f"btn_{cid}"):
                                    st.session_state[f"betting_{cid}"] = True
                        
                        if st.session_state.get(f"betting_{cid}") and user_bet.empty:
                            with st.form(key=f"form_{cid}"):
                                c1, c2 = st.columns(2)
                                ta = c1.number_input(f"{m['team_a']}", 0, 20, 0)
                                tb = c2.number_input(f"{m['team_b']}", 0, 20, 0)
                                if st.form_submit_button("Potvrdit tip"):
                                    new_row = pd.DataFrame([{
                                        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
                                        "user_name": st.session_state.user,
                                        "match_id": cid, "tip_a": int(ta), "tip_b": int(tb), "points_earned": 0
                                    }])
                                    conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_bets, new_row], ignore_index=True))
                                    st.cache_data.clear()
                                    st.session_state[f"betting_{cid}"] = False
                                    st.rerun()
        else:
            st.info("Momentálně nejsou žádné zápasy k tipování.")

    with t2:
        st.subheader("🏆 Aktuální pořadí")
        # Trochu vylepšená tabulka
        leaderboard = df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
        leaderboard.index += 1
        st.table(leaderboard)

    with t3:
        st.subheader("📅 Odehrané zápasy")
        finished = df_matches[df_matches['status'] == 'ukončeno'].copy()
        if not finished.empty:
            finished['Kdy'] = finished['start_time'].dt.strftime('%d.%m. %H:%M')
            st.dataframe(finished[['Kdy', 'group', 'team_a', 'result_a', 'result_b', 'team_b']], hide_index=True)
        else:
            st.write("Zatím se nehrálo.")
else:
    st.warning("👈 Pro tipování se musíš přihlásit v panelu vlevo.")
