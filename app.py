import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date

st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.rerun()
else:
    menu = st.sidebar.radio("Menu", ["Dashboard", "Sair"])
    if menu == "Sair": st.session_state.perfil = None; st.rerun()

    if menu == "Dashboard":
        st.title("📊 Dashboard MJ (Modo Transparente)")
        d_sel = st.sidebar.date_input("Data da Venda", date(2026, 7, 11))
        
        # BUSCA TODAS AS VENDAS SEM FILTRO DE VÍNCULO
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("ns, nome_lojista").execute()
        
        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista'])
            
            # Formata data para bater com o filtro
            df_v['dt_limpa'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt_limpa'].dt.date == d_sel]
            
            if not df_v.empty:
                # Cruza com os lojistas (LEFT JOIN para não sumir com venda não vinculada)
                df = pd.merge(df_v, df_m, on='ns', how='left')
                df['nome_lojista'] = df['nome_lojista'].fillna("⚠️ NÃO VINCULADO")
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)

                st.metric("Total Bruto no Banco", f"R$ {df['bruto_v'].sum():,.2f}")
                st.write(f"Encontradas {len(df)} vendas no banco para o dia {d_sel.strftime('%d/%m')}")
                st.dataframe(df[['data_venda', 'nome_lojista', 'bruto_v', 'ns', 'adquirente']], use_container_width=True)
            else:
                st.info(f"O banco de dados está vazio para o dia {d_sel}. O Robô ainda não enviou os dados ou o SQL limpou a tabela.")
        else:
            st.warning("Não há nenhuma venda cadastrada em nenhum dia.")
