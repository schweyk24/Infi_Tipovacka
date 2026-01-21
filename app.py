import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Infi Tipovačka 2026", layout="wide")

# --- CSS (Bílé pozadí, čistý styl) ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #212529; }
    .logo-container { display: flex; justify-content: center; padding: 20px 0; }
    .match-card {
        background-color: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 25px; border: 1px solid #eee;
    }
    .match-card-bet { border: 2px solid #28a745; background-color: #f8fff9; }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

def get_flag_url(team_name):
    t = str(team_name).strip().upper()
    d = {"CZE":"cz","ČESKO":"cz","ČR":"cz","SVK":"sk","SLOVENSKO":"sk","CAN":"ca","KANADA":"ca","USA":"us","FIN":"fi","FINSKO":"fi","SWE":"se","ŠVÉDSKO":"se","SUI":"ch","ŠVÝCARSKO":"ch","GER":"de","NĚMECKO":"de","LAT":"lv","LOTYŠSKO":"lv","NOR":"no","NORSKO":"no","DEN":"dk","DÁNSKO":"dk","AUT":"at","RAKOUSKO":"at","FRA":"fr","FRANCIE":"fr","KAZ":"kz","KAZACHSTÁN":"kz","ITA":"it","ITÁLIE":"it","SLO":"si","SLOVINSKO":"si","HUN":"hu","MAĎARSKO":"hu"}
    return f"https://flagcdn.com/w80/{d.get(t, 'un')}.png"

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=0).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    df_m.columns = [str(c).lower().strip() for c in df_m.columns]
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True)
    return conn, df_m, df_b, df_u

conn, df_m, df_b, df_u = load_data()

if 'user' not in st.session_state: st.session_state.user = None

st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="250"></div>', unsafe_allow_html=True)

# --- VSTUPNÍ BRÁNA ---
if not st.session_state.user:
    tab_login, tab_reg, tab_forgot = st.tabs(["🔑 Přihlášení", "📝 Registrace", "🆘 Zapomenutý PIN"])
    
    with tab_login:
        with st.form("form_login"):
            u_in = st.text_input("Přezdívka")
            p_in = st.text_input("PIN", type="password")
            if st.form_submit_button("Vstoupit do baru"):
                user_row = df_u[df_u['user_name'].str.lower() == u_in.lower()]
                if not user_row.empty and str(user_row.iloc[0]['pin']) == p_in:
                    st.session_state.user = user_row.iloc[0]['user_name']
                    st.rerun()
                else:
                    st.error("Špatné jméno nebo PIN.")

    with tab_reg:
        st.info("Zvol si unikátní přezdívku. Pokud už ji někdo má, systém tě nepustí.")
        with st.form("form_reg"):
            u_reg = st.text_input("Tvoje přezdívka")
            p_reg = st.text_input("Zvol si 4-místný PIN", max_chars=4)
            phone_3 = st.text_input("Poslední 3 čísla tvého mobilu (pro obnovu PINu)", max_chars=3)
            if st.form_submit_button("Vytvořit účet"):
                if u_reg and p_reg and len(phone_3) == 3:
                    if u_reg.lower() in [name.lower() for name in df_u['user_name']]:
                        st.warning("Tato přezdívka je již obsazená. Zkus jinou nebo se přihlas.")
                    else:
                        new_u = pd.DataFrame([{"user_name": u_reg, "pin": p_reg, "phone_last": phone_3, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_u, new_u]))
                        st.success("Registrace hotová! Teď se můžeš přihlásit v první záložce.")
                else:
                    st.error("Vyplň prosím všechna pole (jméno, PIN i 3 čísla mobilu).")

    with tab_forgot:
        st.subheader("Zapomněl jsi PIN?")
        with st.form("form_recovery"):
            u_rec = st.text_input("Zadej svou přezdívku")
            ph_rec = st.text_input("Zadej poslední 3 čísla mobilu")
            if st.form_submit_button("Ukázat můj PIN"):
                user_row = df_u[(df_u['user_name'].str.lower() == u_rec.lower()) & (df_u['phone_last'].astype(str) == ph_rec)]
                if not user_row.empty:
                    st.success(f"Tvůj PIN je: **{user_row.iloc[0]['pin']}**")
                else:
                    st.error("Přezdívka a čísla mobilu nesouhlasí.")

# --- HRÁČSKÁ SEKCE ---
else:
    u_row = df_u[df_u['user_name'] == st.session_state.user]
    pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    
    st.markdown(f"<h3 style='text-align: center;'>Vítej, {st.session_state.user}! 🏒 | Tvůj stav: {pts} bodů</h3>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📝 TIPOVAT", "🏆 ŽEBŘÍČEK", "✅ VÝSLEDKY"])
    
    with t1:
        # Zde zůstává ta vyladěná logika s kartami zápasů z předchozího kroku...
        st.write("Tady budou karty se zápasy k tipování.")

    if st.button("Odhlásit se"):
        st.session_state.user = None
        st.rerun()
