import streamlit as st
import pandas as pd
from supabase import create_client, Client
import streamlit_authenticator as stauth

# 1. Configuração da Página
st.set_page_config(page_title="Painel MJ", layout="centered")

# 2. Dados de Login
# Senha: admin123
credentials = {
    "usernames": {
        "admin": {
            "name": "Marivaldo Júnior",
            "password": "$2b$12$LO9.6oK7C/M6vO8U0zO/aeA7S9V8K/6/7P/9.Z2GqO8m8Rk8v0v."
        }
    }
}

# 3. Inicialização do Autenticador (Usando argumentos nomeados para evitar erros)
authenticator = stauth.Authenticate(
    credentials=credentials,
    cookie_name="mj_dashboard_v8",
    key="mj_secret_v8",
    cookie_expiry_days=30
)

# 4. Renderiza o formulário de login
# O formulário agora só será renderizado se ninguém estiver logado
if not st.session_state.get("authentication_status"):
    st.title("🔒 Acesso Restrito")
    authenticator.login()

# 5. Lógica da Área Logada
if st.session_state.get("authentication_status"):
    # Se chegou aqui, o login deu certo!
    st.sidebar.title(f"Bem-vindo, {st.session_state['name']}")
    authenticator.logout('Sair', 'sidebar')

    st.title("📊 Painel Geral MJ")
    st.success("Logado com sucesso!")

    # --- SÓ AGORA CONECTA NO SUPABASE ---
    URL_SB = "https://oiuyklgtcazbtuvwmelv.supabase.co"
    # COLOQUE SUA KEY REAL ABAIXO
    KEY_SB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 

    try:
        supabase = create_client(URL_SB, KEY_SB)
        res = supabase.table("vendas").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            df = df[df['lojista'].notna() & (df['lojista'].str.lower() != 'nan')]
            st.metric("Total de Vendas", len(df))
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhuma venda encontrada no banco.")
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

elif st.session_state.get("authentication_status") is False:
    st.error('Usuário ou senha incorretos.')

elif st.session_state.get("authentication_status") is None:
    st.info('Utilize admin / admin123')
