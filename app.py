import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Infi Tipovačka 2026", layout="wide")

# --- SVĚTLÝ DESIGN (CSS) ---
st.markdown("""
    <style>
    /* Pozadí a fonty */
    .stApp { background-color: #f8f9fa; color: #212529; }
    
    /* Karty pro zápasy */
    .match-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border: 1px solid #e9ecef;
    }
    
    /* Pravidla box */
    .rules-box {
        background-color: #e9ecef;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #e63946;
    }

    /* Tlačítka */
    .stButton>button {
        border-radius: 10px;
        background-color: #e63946;
        color: white;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
    }
    
    /* Skrytí bočního panelu na mobilu pro čistý vzhled */
    [data-testid="stSidebar"] { display: none; }
    
    /* Horní lišta */
    .header-logo { text-align: center; padding: 20px; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

def get_flag_url(team_name):
    team = str(team_name).strip().upper()
    codes = {"CZE": "cz", "ČESKO": "cz", "SVK": "sk", "SLOVENSKO": "sk", "CAN": "ca", "KANADA": "ca", "USA": "us", "FIN": "fi", "SWE": "se", "SUI": "ch", "GER": "de", "LAT": "lv", "NOR": "no", "DEN": "dk", "AUT": "at", "FRA": "fr", "KAZ": "kz", "ITA": "it", "SLO": "si", "HUN": "hu"}
    code = codes.get(team, "un")
    return f"https://flagcdn.com/w80/{code}.png"

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

conn, df_matches, df_bets, df_users = load_data()

if 'user' not in st.session_state:
    st.session_state.user = None

# --- HLAVNÍ LOGO ---
st.image(LOGO_URL, width=250)
st.markdown("<div style='text-align: center; color: #6c757d; margin-bottom: 30px;'>Oficiální tipovačka zimních her 2026</div>", unsafe_allow_html=True)

# --- LOGIKA STRÁNEK ---
if st.session_state.user is None:
    # --- ÚVODNÍ STRÁNKA (LANDING PAGE) ---
    col_a, col_b = st.columns([1, 1], gap="large")
    
    with col_a:
        st.subheader("📜 Pravidla hry")
        st.markdown("""
        <div class="rules-box">
        1. <b>Přesný výsledek:</b> 5 bodů<br>
        2. <b>Rozdíl skóre / Remíza:</b> 3 body<br>
        3. <b>Vítěz zápasu:</b> 2 body<br>
        <br>
        <i>Sázky se uzavírají 20 minut po začátku utkání.</i>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("🏁 Stav soutěže")
        if not df_users.empty:
            top_3 = df_users.sort_values('total_points', ascending=False).head(5)
            st.table(top_3[['user_name', 'total_points']].rename(columns={'user_name': 'Hráč', 'total_points': 'Body'}))

    with col_b:
        st.subheader("🔑 Vstup do tipovačky")
        with st.form("login_form"):
            u_in = st.text_input("Tvoje přezdívka")
            p_in = st.text_input("PIN (4 čísla)", type="password")
            submit = st.form_submit_button("Přihlásit / Registrovat")
            
            if submit:
                if u_in and len(p_in) == 4:
                    if u_in not in df_users['user_name'].values:
                        new_u = pd.DataFrame([{"user_name": u_in, "pin": p_in, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_users, new_u], ignore_index=True))
                    st.session_state.user = u_in
                    st.rerun()
                else:
                    st.error("Zadej jméno a 4-místný PIN")

    st.divider()
    st.subheader("📅 Přehled dnešních zápasů")
    # Zobrazíme jen náhled zápasů pro nepřihlášené
    preview = df_matches[df_matches['status'] == 'budoucí'].head(3)
    for _, m in preview.iterrows():
        st.markdown(f"🏒 **{m['team_a']} vs {m['team_b']}** — {m['date']} v {m['time']}")

else:
    # --- STRÁNKA PRO PŘIHLÁŠENÉ (Hra) ---
    st.markdown(f"### Vítej, {st.session_state.user}! 👋")
    
    t1, t2, t3 = st.tabs(["📝 TIPOVAT", "📊 ŽEBŘÍČEK", "✅ VÝSLEDKY"])
    
    with t1:
        now = datetime.now()
        open_m = df_matches[(df_matches['status'] == 'budoucí') & (df_matches['internal_datetime'] > (now - timedelta(minutes=20)))]
        
        if not open_m.empty:
            for _, m in open_m.iterrows():
                cid = str(m['match_id'])
                user_bet = df_bets[(df_bets['user_name'] == st.session_state.user) & (df_bets['match_id'] == cid)]
                
                # KARTA ZÁPASU
                st.markdown(f"""
                <div class="match-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="text-align: center; width: 40%;">
                            <img src="{get_flag_url(m['team_a'])}" width="60"><br>
                            <b>{m['team_a']}</b>
                        </div>
                        <div style="text-align: center; width: 20%; font-size: 20px; font-weight: bold;">VS</div>
                        <div style="text-align: center; width: 40%;">
                            <img src="{get_flag_url(m['team_b'])}" width="60"><br>
                            <b>{m['team_b']}</b>
                        </div>
                    </div>
                    <div style="text-align: center; color: #6c757d; margin-top: 10px;">
                        ⏰ {m['time']} | {m['date']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if not user_bet.empty:
                    st.success(f"Tvůj tip: {int(user_bet.iloc[0]['tip_a'])} : {int(user_bet.iloc[0]['tip_b'])}")
                else:
                    # Form přímo v kartě
                    with st.expander("Odeslat tip"):
                        with st.form(key=f"f_{cid}"):
                            c1, c2 = st.columns(2)
                            ta = c1.number_input(f"{m['team_a']}", 0, 20, key=f"ta_{cid}")
                            tb = c2.number_input(f"{m['team_b']}", 0, 20, key=f"tb_{cid}")
                            if st.form_submit_button("Potvrdit"):
                                new_b = pd.DataFrame([{"timestamp": now.strftime("%d.%m. %H:%M"), "user_name": st.session_state.user, "match_id": cid, "tip_a": int(ta), "tip_b": int(tb), "points_earned": 0}])
                                conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_bets, new_b], ignore_index=True))
                                st.cache_data.clear()
                                st.rerun()
        else:
            st.info("Aktuálně nejsou žádné zápasy k tipování.")

    with t2:
        st.subheader("🏆 Celkové pořadí")
        lead = df_users[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
        lead.index += 1
        st.dataframe(lead, use_container_width=True)

    with t3:
        st.subheader("✅ Výsledky odehraných zápasů")
        fin = df_matches[df_matches['status'] == 'ukončeno'].copy()
        if not fin.empty:
            for _, r in fin.iterrows():
                st.markdown(f"**{r['team_a']} {int(r['result_a'])} : {int(r['result_b'])} {r['team_b']}** ({r['date']})")
        else:
            st.write("Zatím žádné výsledky.")

    if st.button("Odhlásit se"):
        st.session_state.user = None
        st.rerun()
