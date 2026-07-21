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

st.title("📊 Portal MJ - Diagnóstico PicPay")
d_sel = st.sidebar.date_input("Filtrar Data", date(2026, 7, 20))

# BUSCA DADOS BRUTOS
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
    
    # --- PROVA REAL: Vendas que o Robô mandou mas o Portal não vinculou ---
    vendas_sem_dono = df_v[~df_v['link'].isin(df_m['link'])]
    if not vendas_sem_dono.empty:
        st.warning(f"⚠️ Atenção: O Robô enviou {len(vendas_sem_dono)} vendas, mas o Portal não sabe de quem elas são.")
        st.write("Copie os números abaixo e cadastre na aba **Vincular** para o cliente PicPay:")
        st.table(vendas_sem_dono[['bruto', 'ns', 'adquirente']])

    # Cruzamento Normal
    df = pd.merge(df_v, df_m, on='link', how='inner')
    if not df.empty:
        df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
        st.success(f"✅ {len(df)} vendas vinculadas com sucesso!")
        st.metric("Total Bruto Vinculado", f"R$ {df['bruto_v'].sum():,.2f}")
        st.dataframe(df[['data_venda', 'nome_lojista', 'bruto_v', 'ns']], use_container_width=True)
    else:
        st.info("Nenhuma venda vinculada encontrada. Verifique os números no aviso amarelo acima.")
else:
    st.error("O banco de dados está vazio. O robô não está conseguindo enviar os dados.")
