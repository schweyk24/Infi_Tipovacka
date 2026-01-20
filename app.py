import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="Hokejová Tipovačka 2026", layout="centered")

# --- PROPOJENÍ A DATA ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_matches = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Matches", ttl=0)
    df_bets = conn.read(spreadsheet=SPREADSHEET_URL, worksheet="Bets", ttl=0)
    
    df_matches['match_id'] = df_matches['match_id'].astype(str)
    if not df_bets.empty:
        df_bets['match_id'] = df_bets['match_id'].astype(str)
except Exception as e:
    st.error(f"Chyba připojení k databázi: {e}")
    st.stop()

# --- STAV PŘIHLÁŠENÍ (Session State) ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR (Menu) ---
st.sidebar.title("🏒 Tipovačka Bar")

if st.session_state.user:
    st.sidebar.success(f"Přihlášen: **{st.session_state.user}**")
    if st.sidebar.button("Odhlásit se"):
        st.session_state.user = None
        st.rerun()
else:
    user_in = st.sidebar.text_input("Tvoje přezdívka")
    pin_in = st.sidebar.text_input("PIN (4 čísla)", type="password")
    if st.sidebar.button("Vstoupit do hry"):
        if user_in and len(pin_in) == 4:
            st.session_state.user = user_in
            st.rerun()
        else:
            st.sidebar.warning("Zadej jméno a 4místný PIN.")

# --- ADMIN SEKCE ---
admin_mode = st.sidebar.checkbox("Režim Barman")
if admin_mode:
    pwd = st.sidebar.text_input("Admin heslo", type="password")
    if pwd == "hokej2026":
        st.header("⚙️ Administrace výsledků")
        
        to_score = df_matches[df_matches['status'] != 'ukončeno']
        if not to_score.empty:
            m_select = st.selectbox("Vyber zápas k vyhodnocení:", to_score['team_a'] + " vs " + to_score['team_b'])
            m_idx = to_score[to_score['team_a'] + " vs " + to_score['team_b'] == m_select].index[0]
            m_id = str(to_score.loc[m_idx, 'match_id'])
            
            c1, c2 = st.columns(2)
            res_a = c1.number_input(f"Skóre {to_score.loc[m_idx, 'team_a']}", min_value=0, step=1)
            res_b = c2.number_input(f"Skóre {to_score.loc[m_idx, 'team_b']}", min_value=0, step=1)
            
            if st.button("✅ Uložit a připsat body všem"):
                def calc_pts(ta, tb, ra, rb):
                    if ta == ra and tb == rb: return 5
                    if (ra-rb) == (ta-tb): return 3
                    if (ra>rb and ta>tb) or (ra<rb and ta<tb): return 2
                    return 0

                if not df_bets.empty:
                    df_bets['points_earned'] = df_bets.apply(
                        lambda x: calc_pts(x['tip_a'], x['tip_b'], res_a, res_b) if x['match_id'] == m_id else x['points_earned'], axis=1
                    )
                
                df_matches.loc[df_matches['match_id'] == m_id, ['result_a', 'result_b', 'status']] = [res_a, res_b, 'ukončeno']
                
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Bets", data=df_bets)
                conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Matches", data=df_matches)
                st.success("Zápas byl vyhodnocen!")
                st.rerun()
        else:
            st.info("Všechny zápasy jsou hotové.")
        st.stop()

# --- HLAVNÍ ROZHRANÍ PRO HRÁČE ---
if st.session_state.user:
    st.title(f"Vítej, {st.session_state.user}!")
    tab1, tab2, tab3 = st.tabs(["📝 Tipovat", "🏆 Pořadí", "📅 Výsledky"])

    with tab1:
        st.subheader("Otevřené zápasy k tipování")
        open_m = df_matches[df_matches['status'] == 'budoucí']
        
        if not open_m.empty:
            m_options = open_m['team_a'] + " vs " + open_m['team_b']
            selected_m = st.selectbox("Vyber zápas:", m_options)
            match_idx = open_m[open_m['team_a'] + " vs " + open_m['team_b'] == selected_m].index[0]
            curr_id = str(open_m.loc[match_idx, 'match_id'])
            
            existing_user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == curr_id)]
            
            if not existing_user_bet.empty:
                st.warning(f"Už máš vsazeno: {int(existing_user_bet.iloc[0]['tip_a'])}:{int(existing_user_bet.iloc[0]['tip_b'])}")
            else:
                col1, col2 = st.columns(2)
                tip_a = col1.number_input(f"Góly {open_m.loc[match_idx, 'team_a']}", min_value=0, step=1, key="tip_a")
                tip_b = col2.number_input(f"Góly {open_m.loc[match_idx, 'team_b']}", min_value=0, step=1, key="tip_b")
                
                if st.button("🚀 Odeslat tip"):
                    new_bet_row = pd.DataFrame([{
                        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "user_name": st.session_state.user,
                        "match_id": curr_id,
                        "tip_a": int(tip_a),
                        "tip_b": int(tip_b),
                        "points_earned": 0
                    }])
                    all_bets = pd.concat([df_bets, new_bet_row], ignore_index=True)
                    conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Bets", data=all_bets)
                    st.balloons()
                    st.success("Tip uložen!")
                    st.rerun()
        else:
            st.info("Žádné zápasy k tipování.")

    with tab2:
        st.subheader("Leaderboard")
        if not df_bets.empty:
            leaderboard = df_bets.groupby('user_name')['points_earned'].sum().reset_index()
            leaderboard.columns = ['Hráč', 'Body']
            leaderboard = leaderboard.sort_values(by='Body', ascending=False)
            st.dataframe(leaderboard, hide_index=True, use_container_width=True)
        else:
            st.write("Zatím žádné tipy.")

    with tab3:
        st.subheader("Odehrané zápasy")
        finished = df_matches[df_matches['status'] == 'ukončeno']
        if not finished.empty:
            st.table(finished[['team_a', 'result_a', 'result_b', 'team_b']])
        else:
            st.write("Zatím nic neodehráno.")
else:
    st.info("👋 Přihlas se vlevo pro vstup do tipovačky.")
