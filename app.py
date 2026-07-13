import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date

st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

def limpar(val): return str(val).strip().upper().lstrip('0') if val else ""

st.title("📊 Dashboard MJ Financeiro")
d_sel = st.sidebar.date_input("Filtrar Data", date(2026, 7, 11))

# BUSCA DADOS
v_res = conn.table("vendas").select("*").execute()
m_res = conn.table("maquinas_ns").select("*").execute()

if v_res.data:
    df_v = pd.DataFrame(v_res.data)
    df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista'])

    # Filtro de Data
    df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
    df_v = df_v[df_v['dt'].dt.date == d_sel]

    # Link NS
    df_v['link'] = df_v['ns'].apply(limpar)
    df_m['link'] = df_m['ns'].apply(limpar)
    
    # Identifica o que não está vinculado
    ns_venda = set(df_v['link'].unique())
    ns_vinculado = set(df_m['link'].unique())
    ns_faltando = ns_venda - ns_vinculado

    if ns_faltando:
        st.warning(f"⚠️ Existem vendas para os seguintes NS não vinculados: {', '.join(ns_faltando)}")
        st.info("Vá na aba 'Vincular' (ou no Supabase) e adicione esses números ao cliente CASH DAY (MJ PAGBANK).")

    df = pd.merge(df_v, df_m, on='link', how='inner')

    if not df.empty:
        df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
        c1, c2 = st.columns(2)
        c1.metric("Faturamento Bruto", f"R$ {df['bruto_v'].sum():,.2f}")
        c2.metric("Total de Vendas", len(df))
        st.dataframe(df[['data_venda', 'nome_lojista', 'bruto_v', 'ns']], use_container_width=True)
    else:
        st.info("Nenhuma venda vinculada encontrada para este dia.")
else:
    st.error("O banco de dados de vendas está vazio.")
