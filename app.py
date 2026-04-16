import streamlit as st
import pandas as pd
from supabase import create_client, Client
import streamlit_authenticator as stauth
from streamlit_autorefresh import st_autorefresh

# 1. Configuração inicial (DEVE ser a primeira linha)
st.set_page_config(page_title="Painel MJ", layout="wide")

# 2. Definição das Credenciais (Senha: admin123)
# O Hash abaixo é o padrão aceito pela versão mais estável do autenticador
credentials = {
    "usernames": {
        "admin": {
            "name": "Marivaldo Júnior",
            "password": "$2b$12$LO9.6oK7C/M6vO8U0zO/aeA7S9V8K/6/7P/9.Z2GqO8m8Rk8v0v."
        }
    }
}

# 3. Inicializa o Autenticador de forma simples
authenticator = stauth.Authenticate(
    credentials,
    "mj_liquida_session", # Nome do cookie
    "mj_secret_key_v5",   # Chave de segurança
    cookie_expiry_days=30
)

# 4. Renderiza o Login (Sem parâmetros extras para não travar)
try:
    # Tenta o método mais recente
    name, authentication_status, username = authenticator.login(location='main')
except:
    # Se falhar, usa o método padrão
    name, authentication_status, username = authenticator.login()

# 5. Lógica de exibição do Dashboard
if st.session_state["authentication_status"]:
    # SÓ ENTRA AQUI SE O LOGIN DER CERTO
    st.sidebar.title(f"Bem-vindo, {st.session_state['name']}")
    authenticator.logout('Sair', 'sidebar')
    
    # Atualiza a página a cada 30 segundos
    st_autorefresh(interval=30000, key="data_refresh")

    st.title("📊 Painel Geral de Vendas")

    # --- CONEXÃO COM O BANCO (SÓ OCORRE APÓS LOGIN) ---
    URL_SB = "https://oiuyklgtcazbtuvwmelv.supabase.co"
    # COLOQUE SUA KEY REAL ABAIXO
    KEY_SB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 

    @st.cache_resource
    def conectar_banco():
        return create_client(URL_SB, KEY_SB)

    def buscar_vendas():
        try:
            supabase = conectar_banco()
            res = supabase.table("vendas").select("*").execute()
            df_raw = pd.DataFrame(res.data)
            if not df_raw.empty:
                # Limpa os nomes 'nan' e vazios
                df_raw = df_raw.dropna(subset=['lojista'])
                df_raw = df_raw[df_raw['lojista'].str.lower() != 'nan']
            return df_raw
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return pd.DataFrame()

    df = buscar_vendas()

    if not df.empty:
        # Métricas rápidas
        col1, col2 = st.columns(2)
        col1.metric("Faturamento Bruto", f"R$ {df['bruto'].astype(float).sum():,.2f}")
        col2.metric("Total de Vendas", len(df))

        st.subheader("📋 Relatório de Transações")
        st.dataframe(df.sort_values(by='id', ascending=False), use_container_width=True)
    else:
        st.info("Aguardando sincronização do robô...")

elif st.session_state["authentication_status"] is False:
    st.error('Usuário ou senha incorretos.')

elif st.session_state["authentication_status"] is None:
    st.info('Sistema MJ - Insira as credenciais para acessar.')
