if st.button("✅ Uložit a připsat body všem"):
    # ... (výpočet bodů) ...
    conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Bets", data=df_bets)
    conn.update(spreadsheet=SPREADSHEET_URL, worksheet="Matches", data=df_matches)
    
    st.cache_data.clear() # TOTO PŘIDAT - vymaže stará data z paměti
    st.success("Zápas byl vyhodnocen!")
    st.rerun()
