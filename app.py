import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

st.title("🧪 Teste de Recebimento de Vendas")
st.write("Abaixo estão as últimas vendas que chegaram no banco de dados (Sem filtros):")

try:
    # Busca as últimas 20 vendas do banco
    res = conn.table("vendas").select("*").order("id", desc=True).limit(20).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        st.success(f"O banco de dados contém {len(df)} registros recentes.")
        st.dataframe(df[['id', 'data_venda', 'bruto', 'adquirente', 'ns']], use_container_width=True)
        
        total = pd.to_numeric(df['bruto'], errors='coerce').sum()
        st.metric("Soma das vendas acima", f"R$ {total:,.2f}")
    else:
        st.error("O banco de dados está vazio. O robô não está conseguindo salvar as informações.")
except Exception as e:
    st.error(f"Erro ao conectar: {e}")

st.info("Dica: Se você rodou o robô e a tabela acima não mudou, o problema é o Pop-up bloqueado no Chrome.")
