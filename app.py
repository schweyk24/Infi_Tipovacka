import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Infi Tipovačka 2026", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #212529; }
    .logo-container { display: flex; justify-content: center; padding: 20px 0; }
    .match-wrapper { margin-bottom: 40px; padding-bottom: 20px; border-bottom: 2px solid #eee; }
    .match-card {
        background-color: white; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #eee;
    }
    .match-card-bet { border: 2px solid #28a745; background-color: #f8fff9; }
    .bet-confirmed { color: #28a745; font-weight: bold; font-size: 1.1em; margin-top: 10px; }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

# --- VLAJKY ---
def get_flag_url(team_name):
    t = str(team_name).strip().upper()
    d = {"CZE":"cz","ČESKO":"cz","ČR":"cz","SVK":"sk","SLOVENSKO":"sk","CAN":"ca","KANADA":"ca","USA":"us","FIN":"fi","FINSKO":"fi","SWE":"se","ŠVÉDSKO":"se","SUI":"ch","ŠVÝCARSKO":"ch","GER":"de","NĚMECKO":"de","LAT":"lv","LOTYŠSKO":"lv","NOR":"no","NORSKO":"no","DEN":"dk","DÁNSKO":"dk","AUT":"at","RAKOUSKO":"at","FRA":"fr","FRANCIE":"fr","KAZ":"kz","KAZACHSTÁN":"kz","ITA":"it","ITÁLIE":"it","SLO":"si","SLOVINSKO":"si","HUN":"hu","MAĎARSKO":"hu"}
    return f"https://flagcdn.com/w80/{d.get(t, 'un')}.png"

# --- NAČÍTÁNÍ DAT ---
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Čteme data s ttl=0 pro okamžitou odezvu
    df_m = conn.read(spreadsheet=URL, worksheet="Matches", ttl=0).dropna(how='all')
    df_b = conn.read(spreadsheet=URL, worksheet="Bets", ttl=0).dropna(how='all')
    df_u = conn.read(spreadsheet=URL, worksheet="Users", ttl=0).dropna(how='all')
    
    # Oprava Matches
    df_m.columns = [str(c).lower().strip() for c in df_m.columns]
    df_m['match_id'] = df_m['match_id'].astype(str)
    df_m['internal_datetime'] = pd.to_datetime(df_m['date'].astype(str) + ' ' + df_m['time'].astype(str), dayfirst=True)
    
    # Oprava Users - NEPRŮSTŘELNÝ FORMÁT
    if not df_u.empty:
        # Převedeme na string a odstraníme .0 u čísel (častá chyba u PINu)
        for col in ['user_name', 'pin', 'phone_last']:
            if col in df_u.columns:
                df_u[col] = df_u[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_u['total_points'] = pd.to_numeric(df_u['total_points'], errors='coerce').fillna(0).astype(int)

    # Oprava Bets
    if not df_b.empty:
        df_b['user_name'] = df_b['user_name'].astype(str).str.strip()
        df_b['match_id'] = df_b['match_id'].astype(str)
        
    return conn, df_m, df_b, df_u

conn, df_m, df_b, df_u = load_data()

# --- LOGO ---
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="250"></div>', unsafe_allow_html=True)

# --- SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None

# --- VSTUPNÍ BRÁNA ---
if not st.session_state.user:
    tab_log, tab_reg, tab_for = st.tabs(["🔑 Přihlášení", "📝 Registrace", "🆘 Zapomenutý PIN"])
    
    with tab_log:
        with st.form("l_form"):
            u_in = st.text_input("Přezdívka (case-sensitive)").strip()
            p_in = st.text_input("PIN (4 čísla)", type="password").strip()
            if st.form_submit_button("Vstoupit do baru"):
                # Porovnáváme přesně podle jména v databázi
                user_match = df_u[df_u['user_name'] == u_in]
                if not user_match.empty:
                    if user_match.iloc[0]['pin'] == p_in:
                        st.session_state.user = user_match.iloc[0]['user_name']
                        st.rerun()
                    else: st.error(f"Špatný PIN pro uživatele {u_in}.")
                else: st.error("Uživatel nenalezen. Zkontroluj velká/malá písmena.")

    with tab_reg:
        with st.form("r_form"):
            u_reg = st.text_input("Nová přezdívka").strip()
            p_reg = st.text_input("Zvol si 4-místný PIN", max_chars=4).strip()
            ph_reg = st.text_input("Poslední 3 čísla mobilu", max_chars=3).strip()
            if st.form_submit_button("Vytvořit účet"):
                if u_reg and p_reg and len(ph_reg) == 3:
                    # Kontrola duplicity (malými písmeny pro jistotu)
                    if u_reg.lower() in [n.lower() for n in df_u['user_name'].tolist()]:
                        st.warning("Tato přezdívka už existuje.")
                    else:
                        new_u = pd.DataFrame([{"user_name": u_reg, "pin": p_reg, "phone_last": ph_reg, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_u, new_u], ignore_index=True))
                        st.cache_data.clear()
                        st.success("Registrace hotová! Teď se můžeš přihlásit.")
                else: st.error("Musíš vyplnit všechna 3 pole!")

    with tab_for:
        with st.form("f_form"):
            u_f = st.text_input("Tvoje přezdívka").strip()
            ph_f = st.text_input("Poslední 3 čísla mobilu").strip()
            if st.form_submit_button("Ukázat můj PIN"):
                # Hledání shody (string na string)
                match = df_u[(df_u['user_name'] == u_f) & (df_u['phone_last'] == ph_f)]
                if not match.empty:
                    st.success(f"Tvůj PIN je: **{match.iloc[0]['pin']}**")
                else: st.error("Neshoda údajů. Zadej přesnou přezdívku a správná 3 čísla.")

# --- HRÁČSKÁ SEKCE ---
else:
    u_row = df_u[df_u['user_name'] == st.session_state.user]
    pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    st.markdown(f"<h3 style='text-align: center;'>Ahoj {st.session_state.user}! 🏒 | Máš {pts} bodů</h3>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📝 TIPOVÁNÍ", "📊 ŽEBŘÍČEK", "✅ VÝSLEDKY"])
    
    with t1:
        now = datetime.now()
        open_m = df_m[(df_m['status'] == 'budoucí') & (df_m['internal_datetime'] > (now - timedelta(minutes=20)))]
        
        if open_m.empty: st.info("Žádné zápasy k tipování.")
        
        for _, m in open_m.iterrows():
            cid = str(m['match_id'])
            user_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == cid)]
            has_bet = not user_bet.empty
            
            # Formátování odpočtu
            lock_time = m['internal_datetime'] + timedelta(minutes=20)
            td = lock_time - now
            timer_str = f"{td.days}d : {td.seconds//3600}h : {(td.seconds//60)%60}m : {td.seconds%60}s"

            st.markdown('<div class="match-wrapper">', unsafe_allow_html=True)
            c_class = "match-card-bet" if has_bet else "match-card"
            st.markdown(f"""
            <div class="{c_class}">
                <div style="display:flex; justify-content:space-between; align-items:center; text-align:center;">
                    <div style="width:35%;"><img src="{get_flag_url(m['team_a'])}" width="60"><br><b>{m['team_a']}</b></div>
                    <div style="width:30%;"><b>VS</b><br><small>{m['date']} {m['time']}</small></div>
                    <div style="width:35%;"><img src="{get_flag_url(m['team_b'])}" width="60"><br><b>{m['team_b']}</b></div>
                </div>
                <p style="text-align:center; margin-top:15px; font-family:monospace; color:#d32f2f;">⏳ Konec sázek: {timer_str}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if has_bet:
                st.markdown(f'<div class="bet-confirmed">✅ Tvůj tip: {int(user_bet.iloc[0]["tip_a"])} : {int(user_bet.iloc[0]["tip_b"])}</div>', unsafe_allow_html=True)
            else:
                with st.expander("➕ ODESLAT TIP"):
                    with st.form(key=f"f{cid}"):
                        c1, c2 = st.columns(2)
                        ta = c1.number_input(m['team_a'], 0, 20, key=f"ta{cid}")
                        tb = c2.number_input(m['team_b'], 0, 20, key=f"tb{cid}")
                        if st.form_submit_button("POTVRDIT"):
                            new_b = pd.DataFrame([{"timestamp": now.strftime("%H:%M"), "user_name": st.session_state.user, "match_id": cid, "tip_a": int(ta), "tip_b": int(tb), "points_earned": 0}])
                            conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_b, new_b], ignore_index=True))
                            st.cache_data.clear(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        if not df_u.empty:
            lead = df_u[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
            lead.index += 1
            st.table(lead.rename(columns={'user_name':'Přezdívka', 'total_points':'Body'}))

    with t3:
        fin = df_m[df_m['status'] == 'ukončeno'].copy()
        if not fin.empty:
            fin['Skóre'] = fin.apply(lambda x: f"{int(x['result_a'])} : {int(x['result_b'])}", axis=1)
            st.table(fin[['date', 'team_a', 'Skóre', 'team_b']].rename(columns={'date':'Datum','team_a':'Tým A','team_b':'Tým B'}))

    if st.button("Odhlásit se"):
        st.session_state.user = None
        st.rerun()
