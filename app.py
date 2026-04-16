import streamlit as st
import pandas as pd
from supabase import create_client, Client
import streamlit_authenticator as stauth
from streamlit_autorefresh import st_autorefresh

# 1. Configuração de Página (Deve ser a primeira linha)
st.set_page_config(page_title="Painel MJ", layout="wide")

# 2. Definição das Credenciais (Senha: admin123)
# O Hash abaixo é o código secreto para 'admin123'
credentials = {
    "usernames": {
        "admin": {
            "name": "Marivaldo Júnior",
            "password": "$2b$12$LO9.6oK7C/M6vO8U0zO/aeA7S9V8K/6/7P/9.Z2GqO8m8Rk8v0v."
        }
    }
}

# 3. Inicializa o Autenticador (Versão ultra-estável)
authenticator = stauth.Authenticate(
    credentials,
    "mj_liquida_v6",     # Nome do cookie
    "mj_random_key_v6",   # Chave secreta
    cookie_expiry_days=30
)

# 4. Renderiza o Login (Apenas UMA vez para não dar erro de duplicidade)
# Se der erro de senha, use 'admin' e 'admin123'
name, authentication_status, username = authenticator.login(location='main')

# 5. Lógica do Dashboard
if st.session_state["authentication_status"]:
    # BOTÃO DE SAIR
    authenticator.logout('Sair', 'sidebar')
    
    # AUTO-REFRESH (30 SEGUNDOS)
    st_autorefresh(interval=30000, key="datarefresh_mj")

    st.title("🚀 Painel de Vendas MJ")
    st.write(f"Bem-vindo, **{st.session_state['name']}**")

    # --- DADOS DO SUPABASE ---
    # Substitua com seus dados reais abaixo:
    URL_SB = "https://oiuyklgtcazbtuvwmelv.supabase.co"
    KEY_SB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 

    @st.cache_resource
    def init_connection():
        return create_client(URL_SB, KEY_SB)

    def load_data():
        try:
            client = init_connection()
            res = client.table("vendas").select("*").execute()
            df_raw = pd.DataFrame(res.data)
            if not df_raw.empty:
                # Limpa lojistas vazios ou 'nan'
                df_raw = df_raw.dropna(subset=['lojista'])
                df_raw = df_raw[df_raw['lojista'].str.lower() != 'nan']
                # Converte para números
                df_raw['bruto'] = pd.to_numeric(df_raw['bruto'], errors='coerce')
            return df_raw
        except Exception as e:
            st.error(f"Erro ao carregar dados do banco: {e}")
            return pd.DataFrame()

    df = load_data()

    if not df.empty:
        # MÉTRICAS RÁPIDAS
        c1, c2, c3 = st.columns(3)
        total_bruto = df['bruto'].sum()
        c1.metric("Faturamento Bruto", f"R$ {total_bruto:,.2f}")
        c2.metric("Total de Vendas", len(df))
        c3.info("Atualizando em tempo real (30s)")

        st.divider()

        # TABELA DE DADOS
        st.subheader("📋 Relatório de Transações")
        st.dataframe(df.sort_values(by='id', ascending=False), use_container_width=True)
    else:
        st.info("Nenhuma venda encontrada no banco. O robô já sincronizou hoje?")

elif st.session_state["authentication_status"] is False:
    st.error('Usuário ou senha incorretos.')

elif st.session_state["authentication_status"] is None:
    st.warning('Por favor, insira o usuário e senha.')

# Rodapé simples
st.caption("Desenvolvido para MJ Soluções Comercial")
