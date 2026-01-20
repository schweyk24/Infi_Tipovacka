import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Hokejová Tipovačka", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

# 1. NAČTENÍ DAT
df_matches = conn.read(worksheet="Matches", ttl=0)
df_bets = conn.read(worksheet="Bets", ttl=0)

# Ošetření ID zápasů na text, aby se to dobře porovnávalo
df_matches['match_id'] = df_matches['match_id'].astype(str)
if not df_bets.empty:
    df_bets['match_id'] = df_bets['match_id'].astype(str)

st.title("🏒 Barová Tipovačka 2026")

# --- SIDEBAR: Identifikace ---
st.sidebar.header("Přihlášení")
user = st.sidebar.text_input("Přezdívka")
pin = st.sidebar.text_input("PIN (4 čísla)", type="password")

# --- ADMINISTRACE (skrytá pod heslem) ---
is_admin = st.sidebar.checkbox("Jsem barman")
if is_admin:
    admin_pass = st.sidebar.text_input("Zadej admin heslo", type="password")
    if admin_pass == "hokej2026": 
        st.header("⚙️ Administrace")
        
        # Výběr zápasu k vyhodnocení (jen ty, co ještě nejsou 'ukončeno')
        matches_to_score = df_matches[df_matches['status'] != 'ukončeno']
        
        if not matches_to_score.empty:
            selected_match_admin = st.selectbox("Vyhodnotit zápas:", matches_to_score['team_a'] + " vs " + matches_to_score['team_b'])
            idx_a = matches_to_score[matches_to_score['team_a'] + " vs " + matches_to_score['team_b'] == selected_match_admin].index[0]
            m_id_admin = str(matches_to_score.loc[idx_a, 'match_id'])
            
            c1, c2 = st.columns(2)
            res_a = c1.number_input(f"Skóre {matches_to_score.loc[idx_a, 'team_a']}", min_value=0, step=1)
            res_b = c2.number_input(f"Skóre {matches_to_score.loc[idx_a, 'team_b']}", min_value=0, step=1)

            if st.button("✅ Uložit výsledek a připsat body"):
                def calculate_points(tip_a, tip_b, real_a, real_b):
                    if tip_a == real_a and tip_b == real_b: return 5
                    r_diff = real_a - real_b
                    t_diff = tip_a - tip_b
                    if (r_diff > 0 and t_diff > 0 and r_diff == t_diff) or (r_diff < 0 and t_diff < 0 and r_diff == t_diff) or (r_diff == 0 and t_diff == 0):
                        return 3
                    if (r_diff > 0 and t_diff > 0) or (r_diff < 0 and t_diff < 0):
                        return 2
                    return 0

                # Výpočet bodů v listu Bets
                if not df_bets.empty:
                    df_bets['points_earned'] = df_bets.apply(
                        lambda x: calculate_points(x['tip_a'], x['tip_b'], res_a, res_b) if x['match_id'] == m_id_admin else x['points_earned'], axis=1
                    )
                
                # Update statusu v Matches
                df_matches.loc[df_matches['match_id'] == m_id_admin, ['result_a', 'result_b', 'status']] = [res_a, res_b, 'ukončeno']
                
                conn.update(worksheet="Bets", data=df_bets)
                conn.update(worksheet="Matches", data=df_matches)
                st.success("Hotovo! Body připsány.")
                st.rerun()
        else:
            st.info("Žádné zápasy k vyhodnocení.")
    else:
        st.warning("Zadej správné admin heslo.")

# --- HLAVNÍ ČÁST PRO HRÁČE (pokud není v admin módu) ---
elif user and pin:
    t1, t2 = st.tabs(["📝 Tipovat", "🏆 Pořadí"])
    
    with t1:
        st.subheader("Zadej svůj tip")
        # Zde kód pro tipování (ten už vám fungoval)
        open_m = df_matches[df_matches['status'] == 'budoucí']
        if not open_m.empty:
            # ... (váš kód pro formulář tipování) ...
            st.write("Vyber zápas a tref výsledek!")
            # POZNÁMKA: Sem vložte tu logiku selectboxu a tlačítka "Odeslat tip" z minula
        else:
            st.info("Žádné otevřené zápasy.")

    with t2:
        st.subheader("Aktuální tabulka hráčů")
        if not df_bets.empty:
            leaderboard = df_bets.groupby('user_name')['points_earned'].sum().reset_index()
            leaderboard.columns = ['Hráč', 'Body']
            leaderboard = leaderboard.sort_values(by='Body', ascending=False)
            st.table(leaderboard)
        else:
            st.write("Zatím žádné tipy v databázi.")

else:
    st.info("Pro tipování a zobrazení výsledků se prosím přihlas vlevo.")
