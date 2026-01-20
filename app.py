import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Hokejová Tipovačka 2026", layout="centered")
URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=60)
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=60)
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=60)
    
    # Převod sloupců na správné typy
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['start_time'] = pd.to_datetime(df_m['start_time'])
    if not df_b.empty:
        df_b['match_id'] = df_b['match_id'].astype(str)
    
    return conn, df_m, df_b, df_u

try:
    conn, df_matches, df_bets, df_users = load_data()
except Exception as e:
    st.error(f"Chyba databáze (Zkontroluj sloupce v Sheets): {e}")
    st.stop()

if 'user' not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR ---
st.sidebar.title("🏒 Tipovačka Bar")
if st.session_state.user:
    st.sidebar.success(f"Přihlášen: {st.session_state.user}")
    if st.sidebar.button("Odhlásit se"):
        st.session_state.user = None
        st.rerun()
else:
    u_in = st.sidebar.text_input("Jméno")
    p_in = st.sidebar.text_input("PIN", type="password")
    if st.sidebar.button("Vstoupit"):
        if u_in and len(p_in) == 4:
            if u_in not in df_users['user_name'].values:
                new_u = pd.DataFrame([{"user_name": u_in, "pin": p_in, "total_points": 0}])
                up_u = pd.concat([df_users, new_u], ignore_index=True)
                conn.update(spreadsheet=URL, worksheet="Users", data=up_u)
                st.cache_data.clear()
            st.session_state.user = u_in
            st.rerun()

# --- ADMIN SEKCE ---
if st.sidebar.checkbox("Barman"):
    pwd = st.sidebar.text_input("Heslo", type="password")
    if pwd == "hokej2026":
        st.header("⚙️ Admin")
        to_s = df_matches[df_matches['status'] != 'ukončeno']
        if not to_s.empty:
            m_sel = st.selectbox("Zápas k vyhodnocení:", to_s['team_a'] + " vs " + to_s['team_b'])
            idx = to_s[to_s['team_a'] + " vs " + to_s['team_b'] == m_sel].index[0]
            m_id = str(to_s.loc[idx, 'match_id'])
            c1, c2 = st.columns(2)
            r_a = c1.number_input(f"Góly {to_s.loc[idx, 'team_a']}", min_value=0)
            r_b = c2.number_input(f"Góly {to_s.loc[idx, 'team_b']}", min_value=0)
            if st.button("✅ Vyhodnotit"):
                def calc(ta, tb, ra, rb):
                    if ta == ra and tb == rb: return 5
                    if (ra-rb) == (ta-tb): return 3
                    if (ra>rb and ta>tb) or (ra<rb and ta<tb): return 2
                    return 0
                if not df_bets.empty:
                    df_bets['points_earned'] = df_bets.apply(
                        lambda x: calc(x['tip_a'], x['tip_b'], r_a, r_b) if x['match_id'] == m_id else x['points_earned'], axis=1
                    )
                df_matches.loc[df_matches['match_id'] == m_id, ['result_a', 'result_b', 'status']] = [r_a, r_b, 'ukončeno']
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
    t1, t2, t3 = st.tabs(["📝 Tipovat", "🏆 Pořadí", "📅 Výsledky"])
    with t1:
        st.subheader("Nové tipy")
        # Časová pojistka: nyní - 20 minut (konec 1. třetiny)
        cutoff_time = datetime.now() - timedelta(minutes=20)
        
        # Zápas musí mít status 'budoucí' A začít před méně než 20 minutami
        op_m = df_matches[
            (df_matches['status'] == 'budoucí') & 
            (df_matches['start_time'] > cutoff_time)
        ]
        
        if not op_m.empty:
            m_opt = op_m['team_a'] + " vs " + op_m['team_b']
            sel_match = st.selectbox("Zápas:", m_opt)
            m_idx = op_m[op_m['team_a'] + " vs " + op_m['team_b'] == sel_match].index[0]
            cid = str(op_m.loc[m_idx, 'match_id'])
            
            # Kontrola stávajícího tipu
            exist = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
            
            if not exist.empty:
                st.warning(f"Tvůj tip: {int(exist.iloc[0]['tip_a'])}:{int(exist.iloc[0]['tip_b'])}")
            else:
                st.info(f"Zápas začíná v: {op_m.loc[m_idx, 'start_time'].strftime('%H:%M')}")
                c1, c2 = st.columns(2)
                ta = c1.number_input(f"Góly {op_m.loc[m_idx, 'team_a']}", 0, 20, 0, key="a")
                tb = c2.number_input(f"Góly {op_m.loc[m_idx, 'team_b']}", 0, 20, 0, key="b")
                if st.button("🚀 Odeslat tip"):
                    new_b = pd.DataFrame([{
                        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "user_name": st.session_state.user,
                        "match_id": cid,
                        "tip_a": int(ta),
                        "tip_b": int(tb),
                        "points_earned": 0
                    }])
                    up_bets = pd.concat([df_bets, new_b], ignore_index=True)
                    conn.update(spreadsheet=URL, worksheet="Bets", data=up_bets)
                    st.cache_data.clear()
                    st.success("Tip uložen!")
                    st.rerun()
        else: 
            st.info("Aktuálně nejsou otevřené žádné zápasy (sázky se uzavírají 20 min po začátku).")
    
    with t2:
        st.subheader("Tabulka")
        st.dataframe(df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False), hide_index=True)
    
    with t3:
        st.subheader("Výsledky")
        st.table(df_matches[df_matches['status'] == 'ukončeno'][['team_a', 'result_a', 'result_b', 'team_b']])
else:
    st.info("Přihlas se vlevo.")
