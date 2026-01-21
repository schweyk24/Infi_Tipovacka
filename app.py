import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Hokejová Tipovačka 2026", layout="centered")

# --- CSS (Design) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #ff4b4b; color: white; font-weight: bold; }
    .stExpander { border: 1px solid #31333f; border-radius: 10px; margin-bottom: 10px; }
    h1, h2, h3 { color: #f0f2f6 !important; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Načtení s ošetřením prázdných řádků
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=2).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=2).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=2).dropna(how='all')
    
    # 1. Zpracování MATCHES
    df_m['match_id'] = df_m['match_id'].astype(str)
    
    # Oprava času: zkusíme start_time, pak kombinaci date+time
    if 'start_time' in df_m.columns:
        df_m['start_time'] = pd.to_datetime(df_m['start_time'], dayfirst=True, errors='coerce')
    elif 'date' in df_m.columns and 'time' in df_m.columns:
        df_m['start_time'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True, errors='coerce')
    
    # Vyčištění statusu (všechno na malá, pryč s mezerami)
    if 'status' in df_m.columns:
        df_m['status'] = df_m['status'].astype(str).str.strip().str.lower()
    
    # 2. Zpracování BETS
    if not df_b.empty:
        df_b['match_id'] = df_b['match_id'].astype(str)
        df_b['points_earned'] = pd.to_numeric(df_b['points_earned'], errors='coerce').fillna(0)

    # 3. Zpracování USERS
    if not df_u.empty:
        df_u['total_points'] = pd.to_numeric(df_u['total_points'], errors='coerce').fillna(0)
    
    return conn, df_m, df_b, df_u

try:
    conn, df_matches, df_bets, df_users = load_data()
except Exception as e:
    st.error(f"Kritická chyba při načítání: {e}")
    st.stop()

if 'user' not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏒 Barová Tipovačka")
    if st.session_state.user:
        st.success(f"Uživatel: {st.session_state.user}")
        # Bezpečné načtení bodů
        u_row = df_users[df_users['user_name'] == st.session_state.user]
        pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
        st.metric("Tvoje body", pts)
        if st.button("Odhlásit se"):
            st.session_state.user = None
            st.rerun()
    else:
        u_in = st.text_input("Přezdívka")
        p_in = st.text_input("PIN", type="password")
        if st.button("Vstoupit"):
            if u_in and p_in:
                if u_in not in df_users['user_name'].values:
                    new_u = pd.DataFrame([{"user_name": u_in, "pin": p_in, "total_points": 0}])
                    conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_users, new_u], ignore_index=True))
                    st.cache_data.clear()
                st.session_state.user = u_in
                st.rerun()

# --- ADMIN ---
if st.sidebar.checkbox("🔒 Režim Barman"):
    pwd = st.sidebar.text_input("Heslo", type="password")
    if pwd == "hokej2026":
        st.header("⚙️ Vyhodnocení")
        # Zobrazíme vše, co není 'ukončeno'
        to_score = df_matches[df_matches['status'] != 'ukončeno'].copy()
        if not to_score.empty:
            for _, m in to_score.iterrows():
                mid = str(m['match_id'])
                with st.container():
                    st.write(f"**{m['team_a']} vs {m['team_b']}**")
                    c1, c2, c3 = st.columns([1,1,1])
                    res_a = c1.number_input(f"Góly {m['team_a']}", 0, 20, 0, key=f"a_{mid}")
                    res_b = c2.number_input(f"Góly {m['team_b']}", 0, 20, 0, key=f"b_{mid}")
                    if c3.button("Uložit", key=f"s_{mid}"):
                        def calc(ta, tb, ra, rb):
                            if ta == ra and tb == rb: return 5
                            if (ra-rb) == (ta-tb): return 3
                            if (ra>rb and ta>tb) or (ra<rb and ta<tb): return 2
                            return 0
                        # Update sázek a bodů
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
                        st.rerun()
        st.stop()

# --- HRÁČI ---
if st.session_state.user:
    t1, t2, t3 = st.tabs(["📝 VSADIT SI", "🏆 ŽEBŘÍČEK", "📅 VÝSLEDKY"])
    
    with t1:
        st.subheader("Aktuální zápasy")
        # Časový zámek 20 minut
        now = datetime.now()
        open_m = df_matches[df_matches['status'] == 'budoucí'].copy()
        
        # Filtr pro zobrazení (jen ty, co ještě nezačaly + 20 min)
        open_m = open_m[open_m['start_time'] > (now - timedelta(minutes=20))]

        if not open_m.empty:
            for _, m in open_m.iterrows():
                cid = str(m['match_id'])
                user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
                
                with st.container():
                    c1, c2 = st.columns([2, 1])
                    c1.markdown(f"**{m['team_a']} vs {m['team_b']}**")
                    c1.caption(f"Skupina {m['group']} | ⏰ {m['start_time'].strftime('%H:%M')}")
                    
                    if not user_bet.empty:
                        c2.success(f"Tip: {int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}")
                    else:
                        if c2.button(f"Tipnout", key=f"b_{cid}"):
                            st.session_state[f"bet_{cid}"] = True
                    
                    if st.session_state.get(f"bet_{cid}") and user_bet.empty:
                        with st.form(key=f"f_{cid}"):
                            ca, cb = st.columns(2)
                            ta = ca.number_input(f"{m['team_a']}", 0, 20, 0)
                            tb = cb.number_input(f"{m['team_b']}", 0, 20, 0)
                            if st.form_submit_button("Potvrdit"):
                                new_b = pd.DataFrame([{"timestamp": now.strftime("%d.%m. %H:%M"), "user_name": st.session_state.user, "match_id": cid, "tip_a": int(ta), "tip_b": int(tb), "points_earned": 0}])
                                conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_bets, new_b], ignore_index=True))
                                st.cache_data.clear()
                                st.session_state[f"bet_{cid}"] = False
                                st.rerun()
        else:
            st.info("Žádné zápasy k tipování.")

    with t2:
        st.subheader("🏆 Leaderboard")
        if not df_users.empty:
            lead = df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False)
            st.table(lead)
        else:
            st.write("Zatím žádní hráči.")

    with t3:
        st.subheader("📅 Poslední výsledky")
        finished = df_matches[df_matches['status'] == 'ukončeno'].copy()
        if not finished.empty:
            st.dataframe(finished[['team_a', 'result_a', 'result_b', 'team_b']], hide_index=True)
        else:
            st.write("Zatím žádné výsledky.")
else:
    st.info("👈 Přihlas se vlevo pro vstup do tipovačky.")
