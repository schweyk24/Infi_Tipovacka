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
    .match-wrapper { margin-bottom: 25px; padding-bottom: 15px; }
    .match-card {
        background-color: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #eee;
    }
    .match-card-bet { border: 2px solid #28a745; background-color: #f8fff9; }
    .match-card-locked { border: 1px solid #ccc; background-color: #f0f0f0; opacity: 0.8; }
    .bet-confirmed { color: #28a745; font-weight: bold; margin-top: 10px; }
    .bet-missed { color: #d32f2f; font-weight: bold; margin-top: 10px; }
    .info-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 20px; }
    [data-testid="stSidebar"] { display: none; }
    .logout-btn { float: right; }
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

if 'user' not in st.session_state: st.session_state.user = None
if 'admin' not in st.session_state: st.session_state.admin = False

st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="250"></div>', unsafe_allow_html=True)

# --- 1. PŘIHLAŠOVACÍ OBRAZOVKA ---
if not st.session_state.user and not st.session_state.admin:
    col_info, col_lead = st.columns([1, 1])
    with col_info:
        st.markdown('<div class="info-box"><h4>📜 Pravidla</h4><p>🎯 <b>5b</b> - Přesný | 🏒 <b>3b</b> - Rozdíl | 🏆 <b>2b</b> - Vítěz</p></div>', unsafe_allow_html=True)
    with col_lead:
        st.markdown("<h4>🏆 TOP 5</h4>", unsafe_allow_html=True)
        if not df_u.empty:
            st.dataframe(df_u.sort_values('total_points', ascending=False).head(5)[['user_name', 'total_points']].rename(columns={'user_name':'Hráč', 'total_points':'Body'}), hide_index=True, use_container_width=True)
    
    st.write("---")
    t_log, t_reg, t_for, t_adm = st.tabs(["🔑 Přihlášení", "📝 Registrace", "🆘 PIN", "🔒 Admin"])
    with t_log:
        with st.form("login"):
            u_in = st.text_input("Přezdívka").strip()
            p_in = st.text_input("PIN", type="password").strip()
            if st.form_submit_button("Vstoupit"):
                match = df_u[df_u['user_name'].str.lower() == u_in.lower()]
                if not match.empty and match.iloc[0]['pin'] == p_in:
                    st.session_state.user = match.iloc[0]['user_name']
                    st.rerun()
                else: st.error("Chyba přihlášení.")
    with t_reg:
        with st.form("reg"):
            u_r, p_r, ph_r = st.text_input("Přezdívka"), st.text_input("PIN (4 čísla)", max_chars=4), st.text_input("3 čísla mobilu", max_chars=3)
            if st.form_submit_button("Registrovat"):
                if u_r and p_r and len(ph_r) == 3:
                    if u_r.lower() in [n.lower() for n in df_u['user_name']]: st.warning("Už existuje.")
                    else:
                        new_u = pd.DataFrame([{"user_name": u_r, "pin": p_r, "phone_last": ph_r, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_u, new_u], ignore_index=True))
                        st.cache_data.clear(); st.success("Hotovo, přihlas se.")
    with t_for:
        with st.form("rec"):
            u_f, ph_f = st.text_input("Přezdívka"), st.text_input("3 čísla mobilu")
            if st.form_submit_button("Ukázat PIN"):
                m = df_u[(df_u['user_name'].str.lower() == u_f.lower()) & (df_u['phone_last'] == ph_f)]
                if not m.empty: st.success(f"Tvůj PIN: {m.iloc[0]['pin']}")
                else: st.error("Nenalezeno.")
    with t_adm:
        pw = st.text_input("Heslo", type="password")
        if st.button("Admin Login"):
            if pw == "hokej2026": st.session_state.admin = True; st.rerun()

# --- 2. ADMIN SEKCE ---
elif st.session_state.admin:
    st.header("⚙️ Admin Panel")
    if st.button("Odhlásit Admina"): st.session_state.admin = False; st.rerun()
    to_score = df_m[df_m['status'] != 'ukončeno'].sort_values('internal_datetime')
    for _, m in to_score.iterrows():
        with st.container():
            st.markdown(f'<div class="admin-card"><b>{m["team_a"]} vs {m["team_b"]}</b></div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            ra, rb = c1.number_input("Skóre A", 0, 20, key=f"a{m['match_id']}"), c2.number_input("Skóre B", 0, 20, key=f"b{m['match_id']}")
            if c3.button("Uložit", key=f"s{m['match_id']}"):
                df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [ra, rb, 'ukončeno']
                # Výpočet bodů (zjednodušeně)
                def calc(ta, tb, ra, rb):
                    if ta == ra and tb == rb: return 5
                    if (ra-rb) == (ta-tb): return 3
                    if (ra > rb and ta > tb) or (ra < rb and ta < tb): return 2
                    return 0
                if not df_b.empty:
                    df_b.loc[df_b['match_id'] == m['match_id'], 'points_earned'] = df_b.apply(lambda x: calc(x['tip_a'], x['tip_b'], ra, rb) if x['match_id'] == m['match_id'] else x['points_earned'], axis=1)
                u_sums = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                df_u = df_u.drop(columns=['total_points']).merge(u_sums, on='user_name', how='left').fillna(0).rename(columns={'points_earned':'total_points'})
                conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                st.cache_data.clear(); st.rerun()

# --- 3. HRÁČSKÁ SEKCE ---
else:
    u_row = df_u[df_u['user_name'] == st.session_state.user]
    pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    
    # HORNÍ LIŠTA
    c_head1, c_head2 = st.columns([4, 1])
    with c_head1: st.subheader(f"🏒 {st.session_state.user} | {pts} bodů")
    with c_head2: 
        if st.button("Odhlásit", type="primary", key="logout_top"): 
            st.session_state.user = None; st.rerun()

    t1, t2 = st.tabs(["📝 TIPOVÁNÍ", "📊 ŽEBŘÍČEK"])
    
    with t1:
        st.markdown("### 📋 Přehled zápasů")
        now = datetime.now()
        # Seřadíme zápasy od nejbližších
        all_matches = df_m.sort_values('internal_datetime')
        
        for _, m in all_matches.iterrows():
            cid = str(m['match_id'])
            user_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == cid)]
            has_bet = not user_bet.empty
            
            # Logika zamčení (20 min po začátku)
            is_locked = now > (m['internal_datetime'] + timedelta(minutes=20))
            is_finished = m['status'] == 'ukončeno'
            
            # Výběr stylu karty
            if is_finished or is_locked: c_style = "match-card-locked"
            elif has_bet: c_style = "match-card-bet"
            else: c_style = "match-card"

            st.markdown(f'<div class="match-wrapper"><div class="match-card {c_style}">', unsafe_allow_html=True)
            
            # Obsah karty
            col1, col2, col3 = st.columns([2, 1, 2])
            with col1: st.image(get_flag_url(m['team_a']), width=40); st.write(f"**{m['team_a']}**")
            with col2: 
                if is_finished: st.markdown(f"### {int(m['result_a'])}:{int(m['result_b'])}")
                else: st.write("VS")
                st.caption(f"{m['time']}")
            with col3: st.image(get_flag_url(m['team_b']), width=40); st.write(f"**{m['team_b']}**")
            
            # Status a tipy
            if is_finished:
                tip_txt = f"{int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}" if has_bet else "Netipnuto"
                st.markdown(f"**Konečný výsledek**. Tvůj tip: `{tip_txt}` | Zisk: **{int(user_bet.iloc[0]['points_earned']) if has_bet else 0}b**")
            elif is_locked:
                if has_bet: st.markdown(f'<p class="bet-confirmed">✅ Tvůj tip: {int(user_bet.iloc[0]["tip_a"])}:{int(user_bet.iloc[0]["tip_b"])} (Zápas probíhá)</p>', unsafe_allow_html=True)
                else: st.markdown('<p class="bet-missed">❌ Na tento zápas už si nemůžeš tipnout.</p>', unsafe_allow_html=True)
            else:
                if has_bet:
                    st.markdown(f'<p class="bet-confirmed">✅ Odesláno: {int(user_bet.iloc[0]["tip_a"])}:{int(user_bet.iloc[0]["tip_b"])}</p>', unsafe_allow_html=True)
                else:
                    with st.expander("➕ ODESLAT TIP"):
                        with st.form(key=f"f{cid}"):
                            c1, c2 = st.columns(2)
                            ta = c1.number_input(m['team_a'], 0, 20, key=f"ta{cid}")
                            tb = c2.number_input(m['team_b'], 0, 20, key=f"tb{cid}")
                            if st.form_submit_button("Potvrdit"):
                                new_b = pd.DataFrame([{"timestamp": now.strftime("%H:%M"), "user_name": st.session_state.user, "match_id": cid, "tip_a": int(ta), "tip_b": int(tb), "points_earned": 0}])
                                conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_b, new_b], ignore_index=True))
                                st.cache_data.clear(); st.rerun()
            
            st.markdown('</div></div>', unsafe_allow_html=True)

    with t2:
        if not df_u.empty:
            lead = df_u[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
            lead.index += 1
            st.table(lead.rename(columns={'user_name':'Přezdívka', 'total_points':'Body'}))
            
    if st.button("Odhlásit se", key="logout_bottom"):
        st.session_state.user = None; st.rerun()
