import streamlit as st
import pandas as pd
from supabase import create_client, Client
import streamlit_authenticator as stauth
from streamlit_autorefresh import st_autorefresh

# 1. Configuração da Página (Primeira linha sempre)
st.set_page_config(page_title="Painel MJ Soluções", layout="wide")

# 2. Definição das Credenciais (Senha: admin123)
credentials = {
    "usernames": {
        "admin": {
            "name": "Marivaldo Júnior",
            "password": "$2b$12$LO9.6oK7C/M6vO8U0zO/aeA7S9V8K/6/7P/9.Z2GqO8m8Rk8v0v."
        }
    }
}

# 3. Inicializa o Autenticador
# Removi parâmetros extras que causam erro em versões novas
authenticator = stauth.Authenticate(
    credentials,
    "mj_liquida_v7",    # Nome do cookie
    "mj_secret_v7",     # Chave do cookie
    30                  # Dias de validade
)

# 4. Renderiza o Login
# Na versão nova, não passamos 'location'. Ele renderiza onde o código for chamado.
authenticator.login()

# 5. Verificação de Status via Session State (Forma mais segura)
if st.session_state.get("authentication_status"):
    # --- ÁREA LOGADA ---
    authenticator.logout('Sair', 'sidebar')
    st_autorefresh(interval=30000, key="refresh_mj")

    st.title("📊 Painel Geral MJ")
    st.write(f"Bem-vindo, {st.session_state['name']}")

    # --- DADOS DO SUPABASE ---
    # COLOQUE SUA KEY REAL ABAIXO
    URL_SB = "https://oiuyklgtcazbtuvwmelv.supabase.co"
    KEY_SB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 

    @st.cache_resource
    def init_db():
        return create_client(URL_SB, KEY_SB)

    def carregar_vendas():
        try:
            client = init_db()
            # Busca as vendas, ordenando pelas mais recentes (id descendente)
            res = client.table("vendas").select("*").order("id", desc=True).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                # Limpa dados ruins
                df = df.dropna(subset=['lojista'])
                df = df[df['lojista'].str.lower() != 'nan']
                # Converte bruto para número
                df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
            return df
        except:
            return pd.DataFrame()

    df = carregar_vendas()

    if not df.empty:
        # Métricas
        total = df['bruto'].sum()
        qtd = len(df)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento Bruto", f"R$ {total:,.2f}")
        c2.metric("Total de Vendas", qtd)
        c3.info("Atualização: 30s")

        st.divider()
        st.subheader("📋 Relatório de Transações")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Aguardando os robôs enviarem as primeiras vendas...")

elif st.session_state.get("authentication_status") is False:
    st.error('Usuário ou senha incorretos.')

elif st.session_state.get("authentication_status") is None:
    st.info('Por favor, insira admin / admin123 para entrar.')
