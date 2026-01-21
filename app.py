import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- KONFIGURACE ---
st.set_page_config(page_title="Infi Tipovačka 2026", layout="wide")

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"

def load_data():
    # ttl=0 zajistí, že se data nebudou držet v paměti stará
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    
    # KLÍČOVÁ OPRAVA: Převedeme důležité sloupce na string a očistíme od mezer
    if not df_u.empty:
        df_u['user_name'] = df_u['user_name'].astype(str).str.strip()
        df_u['pin'] = df_u['pin'].astype(str).str.strip()
        if 'phone_last' in df_u.columns:
            df_u['phone_last'] = df_u['phone_last'].astype(str).str.strip()
    return conn, df_u

conn, df_u = load_data()

if 'user' not in st.session_state: st.session_state.user = None

# --- VSTUPNÍ BRÁNA ---
if not st.session_state.user:
    tab_login, tab_reg, tab_forgot = st.tabs(["🔑 Přihlášení", "📝 Registrace", "🆘 Zapomenutý PIN"])
    
    with tab_login:
        with st.form("form_login"):
            u_in = st.text_input("Přezdívka").strip()
            p_in = st.text_input("PIN", type="password").strip()
            if st.form_submit_button("Vstoupit do baru"):
                # Porovnáváme bez ohledu na velká/malá písmena
                user_match = df_u[df_u['user_name'].str.lower() == u_in.lower()]
                
                if not user_match.empty:
                    saved_pin = str(user_match.iloc[0]['pin'])
                    if saved_pin == p_in:
                        st.session_state.user = user_match.iloc[0]['user_name']
                        st.rerun()
                    else:
                        st.error(f"Špatný PIN. (Zadal jsi: {p_in})")
                else:
                    st.error("Uživatel s touto přezdívkou neexistuje.")

    with tab_reg:
        with st.form("form_reg"):
            u_reg = st.text_input("Nová přezdívka").strip()
            p_reg = st.text_input("Zvol si 4-místný PIN", max_chars=4).strip()
            phone_3 = st.text_input("Poslední 3 čísla tvého mobilu", max_chars=3).strip()
            
            if st.form_submit_button("Vytvořit účet"):
                if u_reg and p_reg and len(phone_3) == 3:
                    if u_reg.lower() in [name.lower() for name in df_u['user_name']]:
                        st.warning("Přezdívka už je zabraná.")
                    else:
                        new_u = pd.DataFrame([{"user_name": u_reg, "pin": p_reg, "phone_last": phone_3, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_u, new_u]))
                        st.cache_data.clear() # Vyčistíme paměť, aby se data hned načetla
                        st.success("Registrace OK! Nyní se můžeš přihlásit.")
                else:
                    st.error("Vyplň všechna pole.")

    with tab_forgot:
        with st.form("form_recovery"):
            u_rec = st.text_input("Tvoje přezdívka").strip()
            ph_rec = st.text_input("Poslední 3 čísla mobilu").strip()
            if st.form_submit_button("Ukázat můj PIN"):
                # Hledání shody jména a čísel telefonu
                recovery_match = df_u[
                    (df_u['user_name'].str.lower() == u_rec.lower()) & 
                    (df_u['phone_last'].astype(str) == ph_rec)
                ]
                if not recovery_match.empty:
                    st.success(f"Tvůj PIN je: **{recovery_match.iloc[0]['pin']}**")
                else:
                    st.error("Nenalezeno. Zkontroluj přezdívku a čísla.")

else:
    st.write(f"Jsi přihlášen jako {st.session_state.user}")
    if st.button("Odhlásit"):
        st.session_state.user = None
        st.rerun()
