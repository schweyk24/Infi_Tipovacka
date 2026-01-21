import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
st.set_page_config(page_title="Infi Tipovačka 2026", layout="wide")

# --- CSS DESIGN ---
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
    .info-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 20px; }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

# --- POMOCNÉ FUNKCE ---
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
    
    if not df_u.empty:
        for col in ['user_name', 'pin', 'phone_last']:
            if col in df_u.columns:
                df_u[col] = df_u[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_u['total_points'] = pd.to_numeric(df_u['total_points'], errors='coerce').fillna(0).astype(int)

    if not df_b.empty:
        df_b['user_name'] = df_b['user_name'].astype(str).str.strip()
        df_b['match_id'] = df_b['match_id'].astype(str)
        
    return conn, df_m, df_b, df_u

conn, df_m, df_b, df_u = load_data()

# --- SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False

# --- LOGO ---
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="250"></div>', unsafe_allow_html=True)

# --- 1. ÚVODNÍ STRÁNKA (Nepřihlášený uživatel) ---
if not st.session_state.user and not st.session_state.admin:
    
    # SEKCE S PRAVIDLY A TOP 5
    col_info, col_lead = st.columns([1, 1])
    
    with col_info:
        st.markdown("""
        <div class="info-box">
            <h4>📜 Pravidla bodování</h4>
            <p>🎯 <b>5 bodů</b> - přesný výsledek<br>
            🏒 <b>3 body</b> - rozdíl skóre nebo remíza<br>
            🏆 <b>2 body</b> - uhodnutý vítěz zápasu</p>
        </div>
        """, unsafe_allow_html=True)

    with col_lead:
        st.markdown("<h4>🏆 Aktuální lídři</h4>", unsafe_allow_html=True)
        if not df_u.empty:
            top_5 = df_u.sort_values('total_points', ascending=False).head(5)
            st.dataframe(top_5[['user_name', 'total_points']].rename(columns={'user_name':'Přezdívka', 'total_points':'Body'}), hide_index=True, use_container_width=True)
        else:
            st.write("Zatím nikdo netipoval.")

    st.write("---")

    # PŘIHLAŠOVACÍ ZÁLOŽKY
    t_log, t_reg, t_for, t_adm = st.tabs(["🔑 Přihlášení", "📝 Registrace", "🆘 Zapomenutý PIN", "🔒 Admin"])
    
    with t_log:
        with st.form("login"):
            u_in = st.text_input("Přezdívka").strip()
            p_in = st.text_input("PIN (4 čísla)", type="password").strip()
            if st.form_submit_button("Vstoupit do hry"):
                match = df_u[df_u['user_name'].str.lower() == u_in.lower()]
                if not match.empty and match.iloc[0]['pin'] == p_in:
                    st.session_state.user = match.iloc[0]['user_name']
                    st.rerun()
                else: st.error("Chybné jméno nebo PIN.")

    with t_reg:
        with st.form("reg"):
            u_r = st.text_input("Nová přezdívka").strip()
            p_r = st.text_input("Zvol si 4-místný PIN", max_chars=4).strip()
            ph_r = st.text_input("Poslední 3 čísla mobilu (pro obnovu)", max_chars=3).strip()
            if st.form_submit_button("Vytvořit účet"):
                if u_r and p_r and len(ph_r) == 3:
                    if u_r.lower() in [n.lower() for n in df_u['user_name'].tolist()]:
                        st.warning("Tato přezdívka už existuje.")
                    else:
                        new_u = pd.DataFrame([{"user_name": u_r, "pin": p_r, "phone_last": ph_r, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_u, new_u], ignore_index=True))
                        st.cache_data.clear()
                        st.success("Registrace hotová! Teď se můžeš přihlásit.")
                else: st.error("Vyplň všechna pole!")

    with t_for:
        with st.form("recovery"):
            u_f = st.text_input("Zadej svou přezdívku").strip()
            ph_f = st.text_input("Poslední 3 čísla mobilu").strip()
            if st.form_submit_button("Ukázat můj PIN"):
                match = df_u[(df_u['user_name'].str.lower() == u_f.lower()) & (df_u['phone_last'] == ph_f)]
                if not match.empty: st.success(f"Tvůj PIN je: **{match.iloc[0]['pin']}**")
                else: st.error("Nenalezeno. Zkontroluj údaje.")

    with t_adm:
        a_pw = st.text_input("Heslo obsluhy", type="password")
        if st.button("Vstoupit do administrace"):
            if a_pw == "hokej2026":
                st.session_state.admin = True; st.rerun()

# --- 2. ADMIN SEKCE ---
elif st.session_state.admin:
    st.header("⚙️ Administrace a vyhodnocení")
    if st.button("⬅️ Odhlásit Admina"): st.session_state.admin = False; st.rerun()
    
    to_score = df_m[df_m['status'] != 'ukončeno'].sort_values('internal_datetime')
    for _, m in to_score.iterrows():
        with st.container():
            st.markdown(f'<div class="admin-card"><b>{m["team_a"]} vs {m["team_b"]}</b> | {m["date"]}</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            rA = c1.number_input("Skóre A", 0, 20, key=f"rA{m['match_id']}")
            rB = c2.number_input("Skóre B", 0, 20, key=f"rB{m['match_id']}")
            if c3.button("Uložit výsledek", key=f"s{m['match_id']}"):
                df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [rA, rB, 'ukončeno']
                def calc(ta, tb, ra, rb):
                    if ta == ra and tb == rb: return 5
                    if (ra-rb) == (ta-tb): return 3
                    if (ra > rb and ta > tb) or (ra < rb and ta < tb): return 2
                    return 0
                if not df_b.empty:
                    df_b.loc[df_b['match_id'] == m['match_id'], 'points_earned'] = df_b.apply(
                        lambda x: calc(x['tip_a'], x['tip_b'], rA, rB) if x['match_id'] == m['match_id'] else x['points_earned'], axis=1
                    )
                user_sums = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                df_u = df_u.drop(columns=['total_points']).merge(user_sums, on='user_name', how='left').fillna(0)
                df_u.rename(columns={'points_earned': 'total_points'}, inplace=True)
                conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                st.cache_data.clear(); st.success("Zápas vyhodnocen!"); st.rerun()

# --- 3. HRÁČSKÁ SEKCE (Po přihlášení) ---
else:
    u_row = df_u[df_u['user_name'] == st.session_state.user]
    pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    st.markdown(f"<h3 style='text-align: center;'>Ahoj {st.session_state.user}! 🏒 | Máš {pts} bodů</h3>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📝 TIPOVÁNÍ", "📊 ŽEBŘÍČEK", "✅ VÝSLEDKY"])
    
    with t1:
        now = datetime.now()
        open_m = df_m[(df_m['status'] == 'budoucí') & (df_m['internal_datetime'] > (now - timedelta(minutes=20)))]
        if open_m.empty: st.info("Momentálně nejsou k dispozici žádné zápasy k tipování.")
        
        for _, m in open_m.iterrows():
            cid = str(m['match_id'])
            user_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == cid)]
            has_bet = not user_bet.empty
            td = (m['internal_datetime'] + timedelta(minutes=20)) - now
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
                st.markdown(f'<div class="bet-confirmed">✅ Tvůj uložený tip: {int(user_bet.iloc[0]["tip_a"])} : {int(user_bet.iloc[0]["tip_b"])}</div>', unsafe_allow_html=True)
            else:
                with st.expander("➕ ODESLAT TIP"):
                    with st.form(key=f"f{cid}"):
                        c1, c2 = st.columns(2)
                        ta = c1.number_input(m['team_a'], 0, 20, key=f"ta{cid}")
                        tb = c2.number_input(m['team_b'], 0, 20, key=f"tb{cid}")
                        if st.form_submit_button("POTVRDIT TIP"):
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
        st.session_state.user = None; st.rerun()
