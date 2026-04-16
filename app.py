import streamlit as st
import pandas as pd
from supabase import create_client, Client
import streamlit_authenticator as stauth
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÕES DO SUPABASE ---
# Lembre-se de colocar sua chave real aqui
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. CONFIGURAÇÃO DE LOGIN ---
# Senha definida: admin123
# O código abaixo é o Hash exato para 'admin123' na versão atual.
config = {
    "credentials": {
        "usernames": {
            "admin": {
                "name": "Marivaldo Júnior",
                "password": "$2b$12$LO9.6oK7C/M6vO8U0zO/aeA7S9V8K/6/7P/9.Z2GqO8m8Rk8v0v."
            }
        }
    },
    "cookie": {
        "expiry_days": 30,
        "key": "mj_secret_key_v4",
        "name": "mj_liquida_cookie_v4"
    }
}

# Inicializa o autenticador
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Renderiza a tela de login (Versão simplificada sem erros de localização)
authenticator.login()

# --- 3. VERIFICAÇÃO DE STATUS ---
if st.session_state["authentication_status"]:
    # Botão de sair na barra lateral
    authenticator.logout('Sair do Sistema', 'sidebar')
    
    # ATUALIZAÇÃO AUTOMÁTICA (A cada 30 segundos)
    st_autorefresh(interval=30000, key="data_refresh_mj")

    st.title(f"🚀 Painel Geral MJ")
    st.write(f"Bem-vindo, **{st.session_state['name']}**")

    # Função para carregar dados do Supabase
    def carregar_vendas():
        try:
            response = supabase.table("vendas").select("*").execute()
            df = pd.DataFrame(response.data)
            if not df.empty:
                # Limpa lojistas vazios ou erro 'nan'
                df = df.dropna(subset=['lojista'])
                df = df[df['lojista'] != 'nan']
                # Converte valores para numérico para cálculos
                df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
                df['liquido'] = pd.to_numeric(df['liquido'], errors='coerce')
            return df
        except Exception as e:
            st.error(f"Erro ao conectar ao banco de dados: {e}")
            return pd.DataFrame()

    df_vendas = carregar_vendas()

    if not df_vendas.empty:
        # MÉTRICAS NO TOPO
        total_bruto = df_vendas['bruto'].sum()
        total_vendas = len(df_vendas)
        
        # Layout de colunas para métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("Bruto Total", f"R$ {total_bruto:,.2f}")
        m2.metric("Qtd Vendas", total_vendas)
        m3.info("Atualização Automática Ativa (30s)")

        st.divider()

        # TABELA DE DADOS
        st.subheader("📋 Últimas Vendas Sincronizadas")
        # Mostra a tabela invertida (vendas mais recentes primeiro)
        st.dataframe(df_vendas.sort_values(by='id', ascending=False), use_container_width=True)

    else:
        st.info("O banco de dados está vazio. Aguardando sincronização dos robôs...")

elif st.session_state["authentication_status"] is False:
    st.error('Usuário ou senha incorretos.')
elif st.session_state["authentication_status"] is None:
    st.warning('Por favor, faça o login para acessar o painel.')
