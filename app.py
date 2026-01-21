import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- URL ZDROJE ---
URL = "https://docs.google.com/spreadsheets/d/1Ujqh0QdVPnp6OA3vOyB7589wPrCf6HJM_JaKDTdp7RU/"
LOGO_URL = "https://raw.githubusercontent.com/schweyk24/Infi_Tipovacka/main/infi_logo_noBG.png"

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(
    page_title="Infi Tipovačka 2026",
    page_icon=LOGO_URL,
    layout="wide"
)

# --- PODPORA PRO IPHONE (Apple Touch Icon) ---
st.markdown(f"""
    <head>
        <link rel="apple-touch-icon" href="{LOGO_URL}">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="default">
    </head>
    """, unsafe_allow_html=True)

# --- CSS DESIGN ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #212529; }
    .logo-container { display: flex; justify-content: center; padding: 10px 0; }
    .match-card {
        background-color: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid #eee;
        margin-bottom: 15px;
    }
    .match-card-bet { border-left: 8px solid #28a745; background-color: #f8fff9; }
    .match-card-locked { border-left: 8px solid #adb5bd; background-color: #f8f9fa; color: #6c757d; }
    .match-header { display: flex; justify-content: space-between; font-size: 0.85em; margin-bottom: 10px; color: #666; }
    .team-name { font-weight: bold; font-size: 1.1em; }
    .timer-text { color: #d32f2f; font-weight: bold; font-family: monospace; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .badge-live { background-color: #ffe3e3; color: #d32f2f; }
    .badge-ok { background-color: #e3fafc; color: #0b7285; }
    .info-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 20px; }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCE ---
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
        df_u['user_name'] = df_u['user_name'].astype(str).str.strip()
        df_u['pin'] = df_u['pin'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_u['phone_last'] = df_u['phone_last'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(3)
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
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="220"></div>', unsafe_allow_html=True)

# --- 1. ÚVODNÍ STRÁNKA ---
if not st.session_state.user and not st.session_state.admin:
    col_info, col_lead = st.columns([1, 1])
    with col_info:
        st.markdown("""
        <div class="info-box">
            <h4>📜 Pravidla bodování</h4>
            <p>🎯 <b>5 bodů</b> - přesný výsledek<br>
            🏒 <b>3 body</b> - stejný rozdíl skóre<br>
            🏆 <b>2 body</b> - uhodnutý vítěz</p>
        </div>
        """, unsafe_allow_html=True)
    with col_lead:
        st.markdown("<h4>🏆 TOP 5 Hráčů</h4>", unsafe_allow_html=True)
        if not df_u.empty:
            top_5 = df_u.sort_values('total_points', ascending=False).head(5)
            st.dataframe(top_5[['user_name', 'total_points']].rename(columns={'user_name':'Přezdívka', 'total_points':'Body'}), hide_index=True, use_container_width=True)
        else:
            st.info("Zatím nikdo netipoval.")
    st.write("---")
    t_log, t_reg, t_for, t_adm = st.tabs(["🔑 Přihlášení", "📝 Registrace", "🆘 Zapomenutý PIN", "🔒 Admin"])
    with t_log:
        with st.form("login"):
            u_in = st.text_input("Přezdívka").strip()
            p_in = st.text_input("PIN", type="password").strip()
            if st.form_submit_button("Vstoupit do baru"):
                match = df_u[df_u['user_name'].str.lower() == u_in.lower()]
                if not match.empty and match.iloc[0]['pin'] == p_in:
                    st.session_state.user = match.iloc[0]['user_name']
                    st.rerun()
                else: st.error("Chybné jméno nebo PIN.")
    with t_reg:
        with st.form("reg"):
            u_r = st.text_input("Nová přezdívka").strip()
            p_r = st.text_input("PIN (4 čísla)", max_chars=4).strip()
            ph_r = st.text_input("Poslední 3 čísla mobilu", max_chars=3).strip()
            if st.form_submit_button("Vytvořit účet"):
                if u_r and p_r and len(ph_r) == 3:
                    if u_r.lower() in [n.lower() for n in df_u['user_name'].tolist()]:
                        st.warning("Přezdívka už existuje.")
                    else:
                        new_u = pd.DataFrame([{"user_name": u_r, "pin": p_r, "phone_last": ph_r, "total_points": 0}])
                        conn.update(spreadsheet=URL, worksheet="Users", data=pd.concat([df_u, new_u], ignore_index=True))
                        st.cache_data.clear(); st.success("Registrace OK! Přejdi na Přihlášení.")
                else: st.error("Vyplň všechna pole!")
    with t_for:
        with st.form("recovery"):
            u_f = st.text_input("Přezdívka").strip()
            ph_f = st.text_input("3 čísla mobilu").strip()
            if st.form_submit_button("Ukázat můj PIN"):
                match = df_u[(df_u['user_name'].str.lower() == u_f.lower()) & (df_u['phone_last'] == ph_f.zfill(3))]
                if not match.empty: st.success(f"Tvůj PIN je: **{match.iloc[0]['pin']}**")
                else: st.error("Nenalezeno.")
    with t_adm:
        a_pw = st.text_input("Admin heslo", type="password")
        if st.button("Vstoupit do administrace"):
            if a_pw == "hokej2026": st.session_state.admin = True; st.rerun()

# --- 2. ADMIN SEKCE ---
elif st.session_state.admin:
    st.header("⚙️ Vyhodnocení zápasů")
    if st.button("⬅️ Odhlásit Admina"): st.session_state.admin = False; st.rerun()
    to_score = df_m[df_m['status'] != 'ukončeno'].sort_values('internal_datetime')
    for _, m in to_score.iterrows():
        with st.container():
            st.write(f"**{m['team_a']} vs {m['team_b']}** ({m['date']})")
            c1, c2, c3 = st.columns(3)
            rA = c1.number_input("Skóre A", 0, 20, key=f"rA{m['match_id']}")
            rB = c2.number_input("Skóre B", 0, 20, key=f"rB{m['match_id']}")
            if c3.button("Uložit", key=f"s{m['match_id']}"):
                df_m.loc[df_m['match_id'] == m['match_id'], ['result_a', 'result_b', 'status']] = [rA, rB, 'ukončeno']
                def calc(ta, tb, ra, rb):
                    if ta == ra and tb == rb: return 5
                    if (ra-rb) == (ta-tb): return 3
                    if (ra > rb and ta > tb) or (ra < rb and ta < tb): return 2
                    return 0
                if not df_b.empty:
                    df_b.loc[df_b['match_id'] == m['match_id'], 'points_earned'] = df_b.apply(lambda x: calc(x['tip_a'], x['tip_b'], rA, rB) if x['match_id'] == m['match_id'] else x['points_earned'], axis=1)
                user_sums = df_b.groupby('user_name')['points_earned'].sum().reset_index()
                df_u = df_u.drop(columns=['total_points']).merge(user_sums, on='user_name', how='left').fillna(0).rename(columns={'points_earned': 'total_points'})
                conn.update(spreadsheet=URL, worksheet="Matches", data=df_m)
                conn.update(spreadsheet=URL, worksheet="Bets", data=df_b)
                conn.update(spreadsheet=URL, worksheet="Users", data=df_u)
                st.cache_data.clear(); st.rerun()

# --- 3. HRÁČSKÁ SEKCE ---
else:
    u_row = df_u[df_u['user_name'] == st.session_state.user]
    pts = int(u_row['total_points'].values[0]) if not u_row.empty else 0
    c_h1, c_h2 = st.columns([5, 1])
    c_h1.subheader(f"🏒 {st.session_state.user} | {pts} bodů")
    if c_h2.button("Odhlásit", key="top_logout"): st.session_state.user = None; st.rerun()
    t1, t2 = st.tabs(["📝 PŘEHLED ZÁPASŮ", "📊 ŽEBŘÍČEK"])
    with t1:
        st.markdown("### 📋 Seznam všech zápasů")
        now = datetime.now()
        all_matches = df_m.sort_values('internal_datetime', ascending=True)
        for _, m in all_matches.iterrows():
            cid = str(m['match_id'])
            user_bet = df_b[(df_b['user_name'] == st.session_state.user) & (df_b['match_id'] == cid)]
            has_bet = not user_bet.empty
            is_finished = m['status'] == 'ukončeno'
            lock_time = m['internal_datetime'] + timedelta(minutes=20)
            is_locked = now > lock_time
            if not is_locked and not is_finished:
                td = lock_time - now
                status_html = f'<span class="timer-text">⏳ Konec za: {td.days}d {td.seconds//3600}h {(td.seconds//60)%60}m</span>'
                c_style = "match-card-bet" if has_bet else "match-card"
            else:
                status_html = '<span class="status-badge badge-live">🔒 Uzavřeno</span>' if not is_finished else '<span class="status-badge badge-ok">✅ Ukončeno</span>'
                c_style = "match-card-locked"
            st.markdown(f"""
            <div class="match-card {c_style}">
                <div class="match-header">
                    <div>📅 {m['date']} | ⏰ {m['time']}</div>
                    <div>{status_html}</div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; text-align:center;">
                    <div style="width:35%;"><img src="{get_flag_url(m['team_a'])}" width="45"><br><span class="team-name">{m['team_a']}</span></div>
                    <div style="width:25%; font-size: 1.5em; font-weight: bold;">{f"{int(m['result_a'])} : {int(m['result_b'])}" if is_finished else "VS"}</div>
                    <div style="width:35%;"><img src="{get_flag_url(m['team_b'])}" width="45"><br><span class="team-name">{m['team_b']}</span></div>
                </div>
            """, unsafe_allow_html=True)
            if is_finished:
                tip = f"{int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}" if has_bet else "Netipnuto"
                st.markdown(f"<hr style='margin:10px 0'><small>Konečný výsledek. Tvůj tip: <b>{tip}</b> | Zisk: <b>{int(user_bet.iloc[0]['points_earned']) if has_bet else 0} b.</b></small>", unsafe_allow_html=True)
            elif is_locked:
                if has_bet: st.markdown(f"<hr style='margin:10px 0'><small>Tvůj tip: <b>{int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}</b> (Probíhá)</small>", unsafe_allow_html=True)
                else: st.markdown("<hr style='margin:10px 0'><small style='color:red;'>Na tento zápas už nelze tipovat.</small>", unsafe_allow_html=True)
            else:
                if has_bet: st.markdown(f"<hr style='margin:10px 0'><small style='color:green;'>✅ Natipováno: <b>{int(user_bet.iloc[0]['tip_a'])}:{int(user_bet.iloc[0]['tip_b'])}</b></small>", unsafe_allow_html=True)
                else:
                    with st.expander("➕ ODESLAT TIP"):
                        with st.form(key=f"f{cid}"):
                            c1, c2 = st.columns(2)
                            ta = c1.number_input(m['team_a'], 0, 20, key=f"ta{cid}")
                            tb = c2.number_input(m['team_b'], 0, 20, key=f"tb{cid}")
                            if st.form_submit_button("Odeslat"):
                                new_b = pd.DataFrame([{"timestamp": now.strftime("%H:%M"), "user_name": st.session_state.user, "match_id": cid, "tip_a": int(ta), "tip_b": int(tb), "points_earned": 0}])
                                conn.update(spreadsheet=URL, worksheet="Bets", data=pd.concat([df_b, new_b], ignore_index=True))
                                st.cache_data.clear(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    with t2:
        if not df_u.empty:
            lead = df_u[['user_name', 'total_points']].sort_values('total_points', ascending=False).reset_index(drop=True)
            lead.index += 1
            st.table(lead.rename(columns={'user_name':'Přezdívka','total_points':'Body'}))
