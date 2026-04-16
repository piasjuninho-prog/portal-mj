import streamlit as st
import pandas as pd
from supabase import create_client

# 1. Configuração da Página (DEVE ser a primeira linha)
st.set_page_config(page_title="Painel MJ", layout="wide")

# 2. Inicializar o estado de login
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# --- FUNÇÃO DE LOGIN ---
def tela_login():
    st.markdown("<h2 style='text-align: center;'>🔒 Acesso Restrito</h2>", unsafe_allow_html=True)
    with st.container():
        user = st.text_input("Usuário", key="user")
        password = st.text_input("Senha", type="password", key="pass")
        if st.button("Entrar no Sistema", use_container_width=True):
            if user == "admin" and password == "admin123":
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

# --- ÁREA DO DASHBOARD ---
def exibir_dashboard():
    if st.sidebar.button("🚪 Sair"):
        st.session_state.autenticado = False
        st.rerun()

    st.title("📊 Dashboard Geral MJ")
    
    # DADOS DO SUPABASE (SÓ CONECTA APÓS LOGIN)
    URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
    KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" # <--- COLOQUE SUA KEY REAL AQUI!

    try:
        supabase = create_client(URL, KEY)
        res = supabase.table("vendas").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)

        if not df.empty:
            # Limpeza rápida
            df = df[df['lojista'].notna() & (df['lojista'] != 'nan')]
            df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
            
            # Métricas
            c1, c2 = st.columns(2)
            c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}")
            c2.metric("Vendas", len(df))
            
            st.divider()
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Aguardando vendas...")
    except Exception as e:
        st.error(f"Erro: {e}")

# --- LÓGICA PRINCIPAL ---
if not st.session_state.autenticado:
    tela_login()
else:
    exibir_dashboard()
