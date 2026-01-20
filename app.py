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
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=10)
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=60)
    
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['start_time'] = pd.to_datetime(df_m['start_time'], dayfirst=True, errors='coerce')
    # Seřazení podle času hned na začátku
    df_m = df_m.sort_values(by='start_time')
    
    if not df_b.empty:
        df_b['match_id'] = df_b['match_id'].astype(str)
    
    return conn, df_m, df_b, df_u

try:
    conn, df_matches, df_bets, df_users = load_data()
except Exception as e:
    st.error(f"Chyba databáze (Zkontroluj sloupec 'group' a 'start_time'): {e}")
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
    p_in = st.sidebar.text_input("PIN (4 čísla)", type="password")
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
if st.sidebar.checkbox("Režim Barman"):
    pwd = st.sidebar.text_input("Heslo", type="password")
    if pwd == "hokej2026":
        st.header("⚙️ Admin")
        to_s = df_matches[df_matches['status'] != 'ukončeno']
        if not to_s.empty:
            m_list = to_s['team_a'] + " vs " + to_s['team_b']
            m_sel = st.selectbox("Zápas:", m_list)
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
        st.subheader("Aktuální nabídka zápasů")
        cutoff = datetime.now() - timedelta(minutes=20)
        
        # Filtrujeme pouze zápasy k tipování
        open_m = df_matches[(df_matches['status'] == 'budoucí') & (df_matches['start_time'] > cutoff)].copy()
        
        if not open_m.empty:
            # Získání unikátních skupin seřazených abecedně
            groups = sorted(open_m['group'].unique())
            
            for g in groups:
                with st.expander(f"Skupina {g}", expanded=True):
                    group_matches = open_m[open_m['group'] == g]
                    
                    for _, m in group_matches.iterrows():
                        cid = str(m['match_id'])
                        match_label = f"{m['team_a']} vs {m['team_b']} ({m['start_time'].strftime('%d.%m. %H:%M')})"
                        
                        # Kontrola, zda uživatel již tipoval
                        user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
                        
                        if not user_bet.empty:
                            # Již vsazeno - barevné info
                            st.success(f"✅ **{match_label}** | Tvůj tip: **{int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}**")
                        else:
                            # Nevsázeno - formulář pro sázku
                            col_txt, col_btn = st.columns([3, 1])
                            col_txt.write(f"⬜ {match_label}")
                            if col_btn.button("Vsadit", key=f"btn_{cid}"):
                                st.session_state[f"betting_{cid}"] = True
                            
                            # Pokud bylo kliknuto na "Vsadit", ukáže se formulář pod tím
                            if st.session_state.get(f"betting_{cid}"):
                                with st.form(key=f"form_{cid}"):
                                    c1, c2 = st.columns(2)
                                    ta = c1.number_input(f"Góly {m['team_a']}", 0, 20, 0, key=f"ta_{cid}")
                                    tb = c2.number_input(f"Góly {m['team_b']}", 0, 20, 0, key=f"tb_{cid}")
                                    if st.form_submit_button("Potvrdit tip"):
                                        new_row = pd.DataFrame([{
                                            "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
                                            "user_name": st.session_state.user,
                                            "match_id": cid,
                                            "tip_a": int(ta),
                                            "tip_b": int(tb),
                                            "points_earned": 0
                                        }])
                                        conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_bets, new_row], ignore_index=True))
                                        st.cache_data.clear()
                                        st.rerun()
        else:
            st.info("Žádné otevřené zápasy k tipování.")

    with t2:
        st.subheader("Tabulka šampionů")
        st.dataframe(df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False), hide_index=True, use_container_width=True)

    with t3:
        st.subheader("Odehrané zápasy")
        finished = df_matches[df_matches['status'] == 'ukončeno'].copy()
        if not finished.empty:
            finished['start_time'] = finished['start_time'].dt.strftime('%d.%m. %H:%M')
            st.table(finished[['group', 'start_time', 'team_a', 'result_a', 'result_b', 'team_b']])
        else:
            st.write("Zatím žádné výsledky.")
else:
    st.info("Přihlas se vlevo pro tipování.")
