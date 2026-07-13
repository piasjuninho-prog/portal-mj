import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date

st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

st.title("📊 Portal MJ - Modo Raio-X")

# 1. TESTE DE CONEXÃO: MOSTRA O QUE TEM NO BANCO AGORA
st.subheader("Últimas 5 vendas que chegaram no banco (Qualquer dia):")
try:
    raw = conn.table("vendas").select("*").order("id", desc=True).limit(5).execute()
    if raw.data:
        st.table(pd.DataFrame(raw.data)[['id', 'data_venda', 'bruto', 'adquirente', 'ns']])
    else:
        st.error("O banco de dados está TOTALMENTE VAZIO. O robô não está conseguindo salvar.")
except Exception as e:
    st.error(f"Erro ao ler banco: {e}")

st.divider()

# 2. DASHBOARD DO DIA
d_sel = st.sidebar.date_input("Filtrar Data", date(2026, 7, 11))
v_res = conn.table("vendas").select("*").execute()

if v_res.data:
    df = pd.DataFrame(v_res.data)
    df['dt_obj'] = pd.to_datetime(df['data_venda'], dayfirst=True, errors='coerce')
    df_hoje = df[df['dt_obj'].dt.date == d_sel]
    
    if not df_hoje.empty:
        st.success(f"Sucesso! Encontramos {len(df_hoje)} vendas para o dia {d_sel}")
        st.metric("Total Bruto", f"R$ {pd.to_numeric(df_hoje['bruto']).sum():,.2f}")
        st.dataframe(df_hoje[['data_venda', 'bruto', 'ns', 'adquirente']], use_container_width=True)
    else:
        st.info("Nenhuma venda encontrada para o dia selecionado nos filtros.")
