import streamlit as st
import pandas as pd
from supabase import create_client, Client
import streamlit_authenticator as stauth
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" # Cole sua chave anon/public aqui
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. GERAÇÃO AUTOMÁTICA DE SENHA SEGURA ---
# O código abaixo gera o código secreto para "admin123" automaticamente
hashed_passwords = stauth.Hasher(['admin123']).generate()

credentials = {
    "usernames": {
        "admin": {
            "name": "Marivaldo Júnior",
            "password": hashed_passwords[0] # Usa a hash gerada na hora
        }
    }
}

# Configura o autenticador
authenticator = stauth.Authenticate(
    credentials,
    "mj_liquida_v3",     # Nome do cookie
    "mj_secret_key_987", # Chave secreta
    cookie_expiry_days=30
)

# Renderiza a tela de login
# Se der erro de "Location", tente apenas: authenticator.login()
try:
    authenticator.login(location='main')
except:
    authenticator.login()

# --- 3. VERIFICAÇÃO DE STATUS ---
if st.session_state["authentication_status"]:
    # BOTÃO DE SAIR
    authenticator.logout('Sair', 'sidebar')
    
    # ATUALIZAÇÃO AUTOMÁTICA (30 SEGUNDOS)
    st_autorefresh(interval=30000, key="data_refresher")

    st.title(f"🚀 Painel Geral MJ")
    st.write(f"Bem-vindo, **{st.session_state['name']}**")

    # Função para carregar dados
    def carregar_vendas():
        try:
            response = supabase.table("vendas").select("*").execute()
            df = pd.DataFrame(response.data)
            if not df.empty:
                # Remove lojistas vazios ou 'nan'
                df = df.dropna(subset=['lojista'])
                df = df[df['lojista'] != 'nan']
                # Converte para números
                df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
                df['liquido'] = pd.to_numeric(df['liquido'], errors='coerce')
            return df
        except Exception as e:
            st.error(f"Erro no banco: {e}")
            return pd.DataFrame()

    df_vendas = carregar_vendas()

    if not df_vendas.empty:
        # MÉTRICAS
        total_bruto = df_vendas['bruto'].sum()
        total_vendas = len(df_vendas)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Bruto Total", f"R$ {total_bruto:,.2f}")
        c2.metric("Qtd Vendas", total_vendas)
        c3.info("Atualizando (30s)")

        st.divider()

        # TABELA
        st.subheader("📋 Últimas Vendas Sincronizadas")
        st.dataframe(df_vendas.sort_values(by='id', ascending=False), use_container_width=True)
    else:
        st.info("Aguardando as primeiras sincronizações do robô...")

elif st.session_state["authentication_status"] is False:
    st.error('Usuário ou senha incorretos.')
elif st.session_state["authentication_status"] is None:
    st.warning('Por favor, faça o login para acessar.')
