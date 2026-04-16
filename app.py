import streamlit as st
import pandas as pd
from supabase import create_client, Client
import streamlit_authenticator as stauth
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" # Use a sua Secret ou Anon Key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. CONFIGURAÇÃO DE LOGIN E COOKIE ---
# Aqui definimos o usuário. Você pode mudar a senha abaixo.
# A senha deve estar criptografada, mas para facilitar, o stauth cuida disso.
credentials = {
    "usernames": {
        "admin": {
            "name": "Marivaldo Júnior",
            "password": "sua_senha_aqui" # Digite sua senha real aqui
        }
    }
}

# Configura o autenticador com COOKIE permanente (30 dias)
authenticator = stauth.Authenticate(
    credentials,
    "mj_liquida_dashboard", # Nome do cookie salvo no navegador
    "mj_secret_key_123",    # Chave para criptografar o cookie
    cookie_expiry_days=30
)

# Renderiza a tela de login
name, authentication_status, username = authenticator.login('Painel MJ - Login', 'main')

# --- 3. LOGICA DO DASHBOARD ---
if authentication_status:
    # Sidebar - Botão de Sair
    authenticator.logout('Sair do Sistema', 'sidebar')
    
    # AUTO-REFRESH: Atualiza a página inteira a cada 30 segundos
    # Isso faz com que novas vendas enviadas pelo robô apareçam sozinhas
    st_autorefresh(interval=30000, key="datarefresh")

    st.title(f"👤 Bem-vindo, {name}")
    st.header("📊 Painel Geral de Vendas MJ")

    # Função para buscar dados do Supabase
    @st.cache_data(ttl=10) # Cache de 10 segundos para não sobrecarregar o banco
    def carregar_vendas():
        response = supabase.table("vendas").select("*").execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            # Limpeza de dados (removendo os 'nan' que comentamos antes)
            df = df.dropna(subset=['lojista'])
            df = df[df['lojista'] != 'nan']
            
            # Garantir que valores são numéricos
            df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
            df['liquido'] = pd.to_numeric(df['liquido'], errors='coerce')
        return df

    df_vendas = carregar_vendas()

    if not df_vendas.empty:
        # --- FILTROS ---
        st.sidebar.header("Filtros")
        lojistas = st.sidebar.multiselect("Filtrar Lojistas:", options=df_vendas['lojista'].unique(), default=df_vendas['lojista'].unique())
        
        df_filtrado = df_vendas[df_vendas['lojista'].isin(lojistas)]

        # --- MÉTRICAS ---
        c1, c2, c3, c4 = st.columns(4)
        total_bruto = df_filtrado['bruto'].sum()
        total_liq = df_filtrado['liquido'].sum()
        total_vendas = len(df_filtrado)
        meu_lucro = total_bruto - total_liq # Exemplo de cálculo

        c1.metric("Bruto Total", f"R$ {total_bruto:,.2f}")
        c2.metric("Líquido Esperado", f"R$ {total_liq:,.2f}")
        c3.metric("Qtd Vendas", total_vendas)
        c4.metric("Seu Lucro (R$)", f"R$ {meu_lucro:,.2f}", delta_color="normal")

        st.divider()

        # --- TABELA DE DADOS ---
        st.subheader("📋 Detalhamento das Transações")
        # Formatação para exibição
        df_display = df_filtrado.copy()
        st.dataframe(df_display, use_container_width=True)

    else:
        st.info("Nenhuma venda encontrada no banco de dados até o momento.")

elif authentication_status == False:
    st.error('Usuário ou senha incorretos.')
elif authentication_status == None:
    st.warning('Por favor, insira seu usuário e senha para acessar o painel.')

# --- RODAPÉ ---
st.caption("Sistema MJ Soluções - Atualização automática ativa (30s)")
