# ... (Partes iniciais iguais) ...

    # --- 🏠 DASHBOARD (v94.0 - CORREÇÃO DE CÁLCULOS) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            df = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            if not df.empty:
                # Deduplicação por NS (ID da transação)
                df = df.drop_duplicates(subset=['ns'], keep='first')
                
                df['data_dt'] = df['data_venda'].apply(converter_data_seguro)
                df = df.dropna(subset=['data_dt'])

                # Filtro de Data
                d_ini = st.sidebar.date_input("Início", date(2026, 6, 8))
                d_fim = st.sidebar.date_input("Fim", date(2026, 6, 8))
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0)
                    df['t_cli'] = pd.to_numeric(df['taxa_cliente'], errors='coerce').fillna(0.0)
                    
                    # Se a taxa for 0, o líquido é igual ao bruto (não some a venda!)
                    df['liq'] = df.apply(lambda x: x['bruto_v'] * (1 - x['t_cli']) if x['t_cli'] > 0 else x['bruto_v'], axis=1)

                    st.title("📊 Dashboard Real")
                    c1, c2, c3 = st.columns(3)
                    # O segredo: Soma o bruto real capturado
                    st.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                    st.metric("Vendas", len(df))

                    st.write("---")
                    st.dataframe(df[['data_venda', 'bandeira', 'plano', 'bruto_v', 'taxa_cliente']].sort_index(ascending=False), use_container_width=True)
