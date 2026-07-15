import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date

st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

st.title("📊 Portal MJ - Monitor de Vendas")

# 1. ÁREA DE DIAGNÓSTICO (O QUE ESTÁ NO BANCO AGORA)
st.subheader("📡 Últimas vendas recebidas pelo banco (Sem filtros)")
try:
    res_raw = conn.table("vendas").select("*").order("data_insercao", desc=True).limit(10).execute()
    if res_raw.data:
        st.table(pd.DataFrame(res_raw.data)[['data_venda', 'bruto', 'adquirente', 'ns']])
    else:
        st.error("O banco de dados está vazio. O robô não está conseguindo enviar.")
except Exception as e:
    st.error(f"Erro ao ler banco: {e}")

st.divider()

# 2. DASHBOARD COM FILTRO
d_sel = st.sidebar.date_input("Filtrar por data", date(2026, 7, 14))
v_res = conn.table("vendas").select("*").execute()
m_res = conn.table("maquinas_ns").select("*").execute()

if v_res.data and m_res.data:
    df_v, df_m = pd.DataFrame(v_res.data), pd.DataFrame(m_res.data)
    df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
    df_v = df_v[df_v['dt'].dt.date == d_sel]
    
    # Cruzamento de dados
    df = pd.merge(df_v, df_m, on='ns', how='inner')
    if not df.empty:
        st.success(f"Sucesso! {len(df)} vendas vinculadas encontradas.")
        st.dataframe(df[['data_venda', 'nome_lojista', 'bruto', 'ns']], use_container_width=True)
    else:
        st.warning("Vendas encontradas, mas nenhum NS está vinculado na aba 'Vincular'.")
