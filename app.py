import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Hokejová Tipovačka 2026", layout="centered")

# --- PROPOJENÍ ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- NAČTENÍ DAT ---
# Matches: match_id, team_a, team_b, status, result_a, result_b
df_matches = conn.read(worksheet="Matches", ttl=0)
# Bets: timestamp, user_name, match_id, tip_a, tip_b, points_earned
df_bets = conn.read(worksheet="Bets", ttl=0)

# Sjednocení typů (match_id musí být vždy string)
df_matches['match_id'] = df_matches['match_id'].astype(str)
if not df_bets.empty:
    df_bets['match_id'] = df_bets['match_id'].astype(str)

st.title("🏒 Barová Tipovačka 2026")

# --- SIDEBAR: PŘIHLÁŠENÍ ---
st.sidebar.header("Uživatel")

# Použijeme session_state pro udržení přihlášení
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

if st.session_state.logged_in_user is None:
    user_input = st.sidebar.text_input("Tvoje Přezdívka")
    pin_input = st.sidebar.text_input("PIN (4 čísla)", type="password")
    if st.sidebar.button("Přihlásit se"):
        if user_input and len(pin_input) == 4:
            st.session_state.logged_in_user = user_input
            st.rerun()
        else:
            st.sidebar.error("Zadej jméno a 4místný PIN")
else:
    st.sidebar.success(f"Přihlášen: **{st.session_state.logged_in_user}**")
    if st.sidebar.button("Odhlásit se"):
        st.session_state.logged_in_user = None
        st.rerun()

# --- ADMIN SEKCE ---
is_admin = st.sidebar.checkbox("Režim Barman")
if is_admin:
    admin_pass = st.sidebar.text_input("Admin heslo", type="password")
    if admin_pass == "hokej2026":
        st.header("⚙️ Administrace")
        # Výběr zápasu, co není ukončený
        m_to_score = df_matches[df_matches['status'] != 'ukončeno']
        if not m_to_score.empty:
            sel_m = st.selectbox("Vyhodnotit zápas:", m_to_score['team_a'] + " vs " + m_to_score['team_b'])
            idx = m_to_score[m_to_score['team_a'] + " vs " + m_to_score['team_b'] == sel_m].index[0]
            m_id = str(m_to_score.loc[idx, 'match_id'])
            
            c1, c2 = st.columns(2)
            res_a = c1.number_input(f"Skóre {m_to_score.loc[idx, 'team_a']}", min_value=0, step=1)
            res_b = c2.number_input(f"Skóre {m_to_score.loc[idx, 'team_b']}", min_value=0, step=1)
            
            if st.button("✅ Potvrdit výsledek"):
                # Výpočet bodů
                def calc_pts(ta, tb, ra, rb):
                    if ta == ra and tb == rb: return 5
                    if (ra-rb == ta-tb): return 3 # Shoda rozdílu/remízy
                    if (ra>rb and ta>tb) or (ra<rb and ta<tb): return 2 # Shoda vítěze
                    return 0

                if not df_bets.empty:
                    df_bets['points_earned'] = df_bets.apply(
                        lambda x: calc_pts(x['tip_a'], x['tip_b'], res_a, res_b) if x['match_id'] == m_id else x['points_earned'], axis=1
                    )
                
                df_matches.loc[df_matches['match_id'] == m_id, ['result_a', 'result_b', 'status']] = [res_a, res_b, 'ukončeno']
                
                conn.update(worksheet="Bets", data=df_bets)
                conn.update(worksheet="Matches", data=df_matches)
                st.success("Zápas vyhodnocen!")
                st.rerun()
        st.stop() # Admin nevidí tipovací část

# --- HLAVNÍ ČÁST PRO HRÁČE ---
if st.session_state.logged_in_user:
    tab1, tab2, tab3 = st.tabs(["📝 Tipovat", "🏆 Pořadí", "📅 Výsledky"])
    
    with tab1:
        st.subheader("Nový tip")
        # Filtrujeme pouze 'budoucí'
        open_m = df_matches[df_matches['status'] == 'budoucí']
        
        if not open_m.empty:
            m_list = open_m['team_a'] + " vs " + open_m['team_b']
            selected_m = st.selectbox("Vyber zápas:", m_list)
            
            idx = open_m[open_m['team_a'] + " vs " + open_m['team_b'] == selected_m].index[0]
            curr_m_id = str(open_m.loc[idx, 'match_id'])
            
            # Kontrola, zda uživatel už netipoval
            user_bets = df_bets[(df_bets['user_name'] == st.session_state.logged_in_user) & (df_bets['match_id'] == curr_m_id)]
            
            if not user_bets.empty:
                st.warning(f"Na zápas {selected_m} už máš vsazeno: {int(user_bets.iloc[0]['tip_a'])}:{int(user_bets.iloc[0]['tip_b'])}")
            else:
                c1, c2 = st.columns(2)
                s_a = c1.number_input(f"Góly {open_m.loc[idx, 'team_a']}", min_value=0, step=1, key="sa")
                s_b = c2.number_input(f"Góly {open_m.loc[idx, 'team_b']}", min_value=0, step=1, key="sb")
                
                if st.button("🚀 Odeslat tip"):
                    new_row = pd.DataFrame([{
                        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "user_name": st.session_state.logged_in_user,
                        "match_id": curr_m_id,
                        "tip_a": int(s_a),
                        "tip_b": int(s_b),
                        "points_earned": 0
                    }])
                    updated_df = pd.concat([df_bets, new_row], ignore_index=True)
                    conn.update(worksheet="Bets", data=updated_df)
                    st.balloons()
                    st.success("Tip uložen!")
                    st.rerun()
        else:
            st.info("Aktuálně nejsou žádné zápasy k tipování.")

    with tab2:
        st.subheader("Leaderboard")
        if not df_bets.empty:
            lb = df_bets.groupby('user_name')['points_earned'].sum().reset_index()
            lb.columns = ['Hráč', 'Body']
            st.dataframe(lb.sort_values('Body', ascending=False), hide_index=True)
        else:
            st.write("Zatím žádné tipy.")

    with tab3:
        st.subheader("Odehrané zápasy")
        st.table(df_matches[df_matches['status'] == 'ukončeno'][['team_a', 'result_a', 'result_b', 'team_b']])

else:
    st.info("Vítej! Pro tipování se prosím přihlas vlevo svou přezdívkou.")
