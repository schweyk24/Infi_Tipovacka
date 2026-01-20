import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Hokejová Tipovačka", layout="centered")

conn = st.connection("gsheets", type=GSheetsConnection)

# Načtení všech listů
df_matches = conn.read(worksheet="Matches", ttl=0)
df_bets = conn.read(worksheet="Bets", ttl=0)

st.title("🏒 Barová Tipovačka 2026")

# --- SIDEBAR: Identifikace ---
st.sidebar.header("Přihlášení")
user = st.sidebar.text_input("Přezdívka")
pin = st.sidebar.text_input("PIN (4 čísla)", type="password")

# --- ADMINISTRACE (skrytá pod heslem) ---
if st.sidebar.checkbox("Jsem barman"):
    admin_pass = st.sidebar.text_input("Zadej admin heslo", type="password")
    if admin_pass == "hokej2026": # Změň si na své heslo
        st.header("⚙️ Administrace")
        st.write("Zde budeš zadávat výsledky a přepočítávat body.")
        # Sem brzy přidáme logiku vyhodnocení
        st.stop() # Zastaví vykonávání zbytku kódu pro admina

# --- ADMINISTRACE (vložit do bloku 'if admin_pass == "hokej2026":') ---
st.header("⚙️ Administrace a Vyhodnocení")

# Vybereme zápas, který chceme vyhodnotit
matches_to_score = df_matches[df_matches['status'] == 'budoucí'] # Nebo změňte na 'probíhá'

if not matches_to_score.empty:
    selected_match_admin = st.selectbox("Vyhodnotit zápas:", matches_to_score['team_a'] + " vs " + matches_to_score['team_b'])
    
    # Získání ID a týmů
    idx_a = matches_to_score[matches_to_score['team_a'] + " vs " + matches_to_score['team_b'] == selected_match_admin].index[0]
    m_id_admin = str(matches_to_score.loc[idx_a, 'match_id'])
    
    col1, col2 = st.columns(2)
    res_a = col1.number_input(f"Konečné skóre {matches_to_score.loc[idx_a, 'team_a']}", min_value=0, step=1)
    res_b = col2.number_input(f"Konečné skóre {matches_to_score.loc[idx_a, 'team_b']}", min_value=0, step=1)

    if st.button("✅ Uložit výsledek a přidělit body"):
        # 1. Funkce pro výpočet bodů
        def calculate_points(tip_a, tip_b, real_a, real_b):
            if tip_a == real_a and tip_b == real_b: return 5  # Přesný výsledek
            
            real_diff = real_a - real_b
            tip_diff = tip_a - tip_b
            
            # Shoda vítěze a rozdílu (nebo remíza)
            if (real_diff > 0 and tip_diff > 0 and real_diff == tip_diff) or \
               (real_diff < 0 and tip_diff < 0 and real_diff == tip_diff) or \
               (real_diff == 0 and tip_diff == 0):
                return 3
            
            # Jen vítěz
            if (real_diff > 0 and tip_diff > 0) or (real_diff < 0 and tip_diff < 0):
                return 2
            
            return 0

        # 2. Update listu Bets
        df_bets.loc[df_bets['match_id'] == m_id_admin, 'points_earned'] = df_bets.apply(
            lambda x: calculate_points(x['tip_a'], x['tip_b'], res_a, res_b) if x['match_id'] == m_id_admin else x['points_earned'], axis=1
        )
        
        # 3. Update listu Matches (nastavíme výsledek a status 'ukončeno')
        df_matches.loc[df_matches['match_id'] == int(m_id_admin), ['result_a', 'result_b', 'status']] = [res_a, res_b, 'ukončeno']
        
        # 4. Zápis do Sheets
        conn.update(worksheet="Bets", data=df_bets)
        conn.update(worksheet="Matches", data=df_matches)
        
        st.success(f"Zápas {selected_match_admin} vyhodnocen! Body byly připsány.")
        st.rerun()

# --- HLAVNÍ ČÁST PRO HRÁČE ---
if user and pin:
    tab1, tab2 = st.tabs(["📝 Tipovat", "🏆 Pořadí"])
    
    with tab1:
        st.subheader("Zadej svůj tip")
        open_matches = df_matches[df_matches['status'] == 'budoucí']
        
        if not open_matches.empty:
            match_list = open_matches['team_a'] + " vs " + open_matches['team_b']
            selected_match = st.selectbox("Vyber zápas:", match_list)
            
            idx = match_list[match_list == selected_match].index[0]
            m_id = str(open_matches.loc[idx, 'match_id'])
            
            # KONTROLA: Už jsi tipoval?
            already_tipped = not df_bets[(df_bets['user_name'] == user) & (df_bets['match_id'] == m_id)].empty
            
            if already_tipped:
                st.warning(f"Na zápas {selected_match} už jsi tipoval!")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    s_a = st.number_input(f"Góly {open_matches.loc[idx, 'team_a']}", min_value=0, step=1)
                with col2:
                    s_b = st.number_input(f"Góly {open_matches.loc[idx, 'team_b']}", min_value=0, step=1)
                
                if st.button("🚀 Odeslat tip"):
                    new_bet = pd.DataFrame([{
                        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "user_name": user,
                        "match_id": m_id,
                        "tip_a": int(s_a),
                        "tip_b": int(s_b),
                        "points_earned": 0
                    }])
                    
                    updated_bets = pd.concat([df_bets, new_bet], ignore_index=True)
                    conn.update(worksheet="Bets", data=updated_bets)
                    st.balloons()
                    st.success("Tip uložen!")
                    st.rerun()
        else:
            st.info("Žádné otevřené zápasy.")

    with tab2:
        st.subheader("Aktuální tabulka")
        # Zde později vypočítáme leaderboard z listu Users
        st.write("Tabulka se začne plnit po prvních odehraných zápasech.")

else:
    st.info("Přihlas se vlevo pro tipování.")
