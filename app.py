import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# Configuração visual do Portal
st.set_page_config(page_title="Portal MJ Soluções", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO SEGURA ---
SUPABASE_URL = st.secrets["supabase"]["https://oiuyklgtcazbtuvwmelv.supabase.co"]
SUPABASE_KEY = st.secrets["supabase"][eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc]

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função para converter a data do robô (Traduzindo meses PT-BR)
def converter_data(data_str):
    try:
        if not data_str: return None
        d = data_str.split(' •')[0].replace(',', '').strip()
        meses = {
            'Jan': '01', 'Fev': '02', 'Mar': '03', 'Abr': '04', 'Mai': '05', 'Jun': '06',
            'Jul': '07', 'Ago': '08', 'Set': '09', 'Out': '10', 'Nov': '11', 'Dez': '12'
        }
        for pt, num in meses.items():
            if pt in d:
                d = d.replace(pt, num)
                break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except:
        return None

# --- SISTEMA DE LOGIN ---
if 'perfil' not in st.session_state:
    st.session_state.perfil = None

if st.session_state.perfil is None:
    st.title("🔑 Portal MJ - Acesso")
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"
            st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"
            st.session_state.usuario = u
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos.")
else:
    # --- MENU LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])

    if menu == "🚪 Sair":
        st.session_state.perfil = None
        st.rerun()

    try:
        # Busca dados do banco
        res_v = conn.table("dashboard_vendas").select("*").execute()
        df = pd.DataFrame(res_v.data)
        
        res_e = conn.table("extrato_consolidado").select("*").execute()
        df_extrato = pd.DataFrame(res_e.data)

        if not df.empty:
            # Tratamento de Data
            df['data_dt'] = df['data_venda'].apply(converter_data)
            df = df.dropna(subset=['data_dt'])

            # --- FILTRO INTELIGENTE DE VISÃO (PONTO CHAVE) ---
            if st.session_state.perfil == "admin":
                st.title("👨‍✈️ Painel Geral MJ (Administrador)")
                lista_lojistas = ["TODOS OS CLIENTES"] + list(df['lojista'].unique())
                escolha = st.sidebar.selectbox("Visualizar Lojista:", lista_filtro = lista_lojistas)
                
                if escolha == "TODOS OS CLIENTES":
                    v_c_full = df.copy()
                    extrato_f = df_extrato.copy() if not df_extrato.empty else pd.DataFrame()
                else:
                    v_c_full = df[df['lojista'] == escolha].copy()
                    extrato_f = df_extrato[df_extrato['lojista']
