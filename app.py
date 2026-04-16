import streamlit as st
import pandas as pd
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh

# 1. Configuração da Página
st.set_page_config(page_title="Painel Geral MJ", layout="wide", page_icon="📊")

# 2. Gerenciamento de Login
if "logado" not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🔐 Acesso Administrativo</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        usuario = st.text_input("Usuário", key="user")
        senha = st.text_input("Senha", type="password", key="pass")
        if st.button("ACESSAR PAINEL", use_container_width=True):
            if usuario == "admin" and senha == "admin123":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

# --- ÁREA DO DASHBOARD (LOGADO) ---
else:
    # Auto-atualização a cada 30 segundos
    st_autorefresh(interval=30000, key="datarefresh")

    # BARRA LATERAL (FILTROS)
    st.sidebar.title("MENU MJ")
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # --- CONEXÃO SUPABASE ---
    URL_SB = "https://oiuyklgtcazbtuvwmelv.supabase.co"
    KEY_SB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 

    @st.cache_resource
    def conectar():
        return create_client(URL_SB, KEY_SB)

    def carregar_vendas():
        try:
            sb = conectar()
            res = sb.table("vendas").select("*").order("id", desc=True).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                # Limpeza de dados
                df = df.dropna(subset=['lojista'])
                df = df[df['lojista'].str.lower() != 'nan']
                # Garante que são números
                df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
                df['liquido'] = pd.to_numeric(df['liquido'], errors='coerce').fillna(0)
                df['spread_rs'] = pd.to_numeric(df['spread_rs'], errors='coerce').fillna(0)
            return df
        except:
            return pd.DataFrame()

    df_vendas = carregar_vendas()

    st.title("📊 Dashboard MJ Soluções")

    if not df_vendas.empty:
        # --- SISTEMA DE FILTROS NA SIDEBAR ---
        st.sidebar.divider()
        st.sidebar.subheader("Filtrar Resultados")
        
        # Filtro de Lojistas
        lista_lojistas = sorted(df_vendas['lojista'].unique())
        selecionados = st.sidebar.multiselect("Filtrar Lojistas:", options=lista_lojistas, default=lista_lojistas)
        
        # Aplica o filtro
        df_filtrado = df_vendas[df_vendas['lojista'].isin(selecionados)]

        # --- MÉTRICAS (VOLTARAM!) ---
        c1, c2, c3, c4 = st.columns(4)
        
        total_bruto = df_filtrado['bruto'].sum()
        total_vendas = len(df_filtrado)
        total_liquido = df_filtrado['liquido'].sum()
        total_lucro = df_filtrado['spread_rs'].sum()

        c1.metric("Bruto Total", f"R$ {total_bruto:,.2f}")
        c2.metric("Líquido Esperado", f"R$ {total_liquido:,.2f}")
        c3.metric("Qtd Vendas", total_vendas)
        c4.metric("Seu Lucro (Spread)", f"R$ {total_lucro:,.2f}")

        st.divider()

        # TABELA DE VENDAS
        st.subheader("📋 Relatório de Transações")
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.info("Aguardando novas sincronizações...")

    st.caption("Atualização automática ativa (30s)")
