import streamlit as st
import pandas as pd
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh

# 1. Configuração da Página
st.set_page_config(page_title="Painel Geral MJ", layout="wide", page_icon="📊")

# 2. Gerenciamento de Login (Mantendo o que funcionou)
if "logado" not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🔐 Acesso Administrativo</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.info("Digite suas credenciais abaixo")
        usuario = st.text_input("Usuário", key="user")
        senha = st.text_input("Senha", type="password", key="pass")
        if st.button("ACESSAR PAINEL", use_container_width=True):
            if usuario == "admin" and senha == "admin123":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

# --- ÁREA DO DASHBOARD (SÓ ABRE SE LOGADO) ---
else:
    # AUTO-REFRESH: Atualiza a página inteira a cada 30 segundos
    st_autorefresh(interval=30000, key="datarefresh")

    # BARRA LATERAL
    st.sidebar.title("MENU MJ")
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    st.title("📊 Dashboard MJ Soluções")
    st.write("Dados atualizados em tempo real diretamente do banco.")

    # --- CONFIGURAÇÃO SUPABASE ---
    URL_SB = "https://oiuyklgtcazbtuvwmelv.supabase.co"
    KEY_SB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 

    @st.cache_resource
    def conectar():
        return create_client(URL_SB, KEY_SB)

    def carregar_vendas():
        try:
            sb = conectar()
            # Busca as vendas, ordenando pelas mais recentes (ID maior primeiro)
            res = sb.table("vendas").select("*").order("id", desc=True).execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                # Limpa lojistas vazios ou 'nan'
                df = df.dropna(subset=['lojista'])
                df = df[df['lojista'].str.lower() != 'nan']
                # Garante que os valores são números para somar
                df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
            return df
        except Exception as e:
            st.error(f"Erro ao conectar ao banco: {e}")
            return pd.DataFrame()

    df_vendas = carregar_vendas()

    if not df_vendas.empty:
        # MÉTRICAS NO TOPO
        total_bruto = df_vendas['bruto'].sum()
        total_vendas = len(df_vendas)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento Bruto", f"R$ {total_bruto:,.2f}")
        c2.metric("Qtd de Vendas", total_vendas)
        c3.success("Robôs em Operação")

        st.divider()

        # TABELA DE VENDAS
        st.subheader("📋 Últimas Vendas Sincronizadas")
        st.dataframe(df_vendas, use_container_width=True)
    else:
        st.warning("Aguardando as primeiras vendas caírem no banco de dados...")

    st.caption("Sistema MJ Soluções - Atualização automática a cada 30s ativa.")
