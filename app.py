import streamlit as st
import pandas as pd
from supabase import create_client, Client
import streamlit_authenticator as stauth
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÕES INICIAIS DA PÁGINA ---
st.set_page_config(page_title="Painel MJ", page_icon="🚀", layout="wide")

# --- 2. DADOS DE CONEXÃO (VERIFIQUE SE ESTÃO CORRETOS!) ---
# IMPORTANTE: Se as chaves abaixo estiverem como "SUA_KEY...", o site vai travar!
URL_SB = "https://oiuyklgtcazbtuvwmelv.supabase.co"
KEY_SB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 

# Inicializa o banco de dados de forma segura
@st.cache_resource
def get_supabase():
    return create_client(URL_SB, KEY_SB)

# --- 3. CONFIGURAÇÃO DE LOGIN ---
# Senha: admin123
credentials = {
    "usernames": {
        "admin": {
            "name": "Marivaldo Júnior",
            "password": "$2b$12$LO9.6oK7C/M6vO8U0zO/aeA7S9V8K/6/7P/9.Z2GqO8m8Rk8v0v."
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "mj_session_cookie",
    "mj_random_key_99",
    cookie_expiry_days=30
)

# Renderiza o formulário de login
# Se a tela continuar cinza, mude para: authenticator.login(location='main')
authenticator.login()

# --- 4. ÁREA LOGADA ---
if st.session_state["authentication_status"]:
    # Sidebar
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    st.sidebar.title(f"Olá, {st.session_state['name']}")
    authenticator.logout('Sair do Sistema', 'sidebar')
    
    # ATUALIZAÇÃO AUTOMÁTICA (30s)
    st_autorefresh(interval=30000, key="f5_data")

    st.title("📊 Dashboard MJ Soluções")
    st.markdown("---")

    # Função para carregar dados do Supabase
    def carregar_dados():
        try:
            sb = get_supabase()
            response = sb.table("vendas").select("*").execute()
            df = pd.DataFrame(response.data)
            if not df.empty:
                df = df[df['lojista'].notna() & (df['lojista'] != 'nan')]
                df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
                df['liquido'] = pd.to_numeric(df['liquido'], errors='coerce')
                return df
            return pd.DataFrame()
        except:
            return pd.DataFrame()

    df = carregar_dados()

    if not df.empty:
        # MÉTRICAS EXECUTIVAS
        bruto_total = df['bruto'].sum()
        qtd = len(df)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Faturamento Bruto", f"R$ {bruto_total:,.2f}")
        col2.metric("Total de Vendas", qtd)
        col3.success("Sincronização Ativa")

        st.subheader("📋 Relatório de Vendas Recentes")
        # Exibe as 50 últimas vendas
        st.table(df.sort_values(by='id', ascending=False).head(50))
    else:
        st.info("Aguardando dados dos robôs...")

elif st.session_state["authentication_status"] is False:
    st.error('Usuário ou senha incorretos.')
    
elif st.session_state["authentication_status"] is None:
    st.info('Por favor, insira suas credenciais para acessar o painel administrativo.')
