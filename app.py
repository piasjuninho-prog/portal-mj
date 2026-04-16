import streamlit as st
import pandas as pd
from supabase import create_client, Client
import streamlit_authenticator as stauth
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÕES DO SUPABASE ---
# Substitua com seus dados reais do Supabase
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. CONFIGURAÇÃO DE LOGIN ---
# Usei a senha "admin123". O código abaixo é a versão criptografada dela.
credentials = {
    "usernames": {
        "admin": {
            "name": "Marivaldo Júnior",
            "password": "$2b$12$LO9.6oK7C/M6vO8U0zO/aeA7S9V8K/6/7P/9.Z2GqO8m8Rk8v0v." 
        }
    }
}

# Configura o autenticador
authenticator = stauth.Authenticate(
    credentials,
    "mj_liquida_cookie",
    "mj_key_secret_123",
    cookie_expiry_days=30
)

# Chama a tela de login (Ajustado para a versão nova)
authenticator.login(location='main')

# --- 3. VERIFICAÇÃO DE STATUS ---
if st.session_state["authentication_status"]:
    # BOTÃO DE SAIR NA BARRA LATERAL
    authenticator.logout('Sair', 'sidebar')
    
    # ATUALIZAÇÃO AUTOMÁTICA A CADA 30 SEGUNDOS
    st_autorefresh(interval=30000, key="data_refresher")

    st.title(f"🚀 Painel Geral MJ")
    st.write(f"Bem-vindo, **{st.session_state['name']}**")

    # Função para carregar dados
    def carregar_vendas():
        try:
            response = supabase.table("vendas").select("*").execute()
            df = pd.DataFrame(response.data)
            if not df.empty:
                # Limpa lojistas vazios ou erro 'nan'
                df = df.dropna(subset=['lojista'])
                df = df[df['lojista'] != 'nan']
                # Garante que os números são reais para os cálculos
                df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
                df['liquido'] = pd.to_numeric(df['liquido'], errors='coerce')
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
        c1.metric("Bruto Total", f"R$ {total_bruto:,.2f}")
        c2.metric("Qtd Vendas", total_vendas)
        c3.info("Atualizando em tempo real (30s)")

        st.divider()

        # TABELA DE VENDAS
        st.subheader("📋 Últimas Sincronizações")
        st.dataframe(df_vendas.sort_values(by='id', ascending=False), use_container_width=True)

    else:
        st.info("Aguardando as primeiras sincronizações do robô...")

elif st.session_state["authentication_status"] is False:
    st.error('Usuário ou senha incorretos.')
elif st.session_state["authentication_status"] is None:
    st.warning('Por favor, utilize o formulário para acessar.')
