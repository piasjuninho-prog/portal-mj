import streamlit as st
import pandas as pd
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh

# 1. Configuração da Página
st.set_page_config(page_title="Painel MJ Soluções", layout="wide")

# 2. Configurações do Supabase (COLE SUA KEY REAL AQUI)
URL_SB = "https://oiuyklgtcazbtuvwmelv.supabase.co"
KEY_SB = "SUA_KEY_ANON_OU_PUBLIC_AQUI" 

# Inicializa o banco de dados
@st.cache_resource
def conectar_banco():
    return create_client(URL_SB, KEY_SB)

# 3. Gerenciamento de Login Simples (Não trava)
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    # --- TELA DE LOGIN ---
    st.markdown("<h1 style='text-align: center;'>🔒 Acesso Restrito</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            btn_entrar = st.form_submit_button("Entrar no Painel")
            
            if btn_entrar:
                if usuario == "admin" and senha == "admin123":
                    st.session_state.logado = True
                    st.rerun() # Reinicia para mostrar o painel
                else:
                    st.error("Usuário ou senha incorretos")
    st.info("Utilize admin / admin123")

else:
    # --- ÁREA LOGADA (DASHBOARD) ---
    
    # Botão de Sair no topo da lateral
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # Atualização Automática a cada 30 segundos
    st_autorefresh(interval=30000, key="datarefresh")

    st.title("📊 Dashboard Geral MJ")
    st.write("Sincronização em tempo real ativa.")

    def carregar_vendas():
        try:
            sb = conectar_banco()
            # Busca as vendas ordenando pelas mais recentes
            res = sb.table("vendas").select("*").order("id", desc=True).execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                # Limpa dados 'nan'
                df = df.dropna(subset=['lojista'])
                df = df[df['lojista'].str.lower() != 'nan']
                # Converte para números
                df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce')
            return df
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            return pd.DataFrame()

    df_vendas = carregar_vendas()

    if not df_vendas.empty:
        # MÉTRICAS
        total_bruto = df_vendas['bruto'].sum()
        total_vendas = len(df_vendas)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento Bruto", f"R$ {total_bruto:,.2f}")
        m2.metric("Qtd de Vendas", total_vendas)
        m3.success("Robôs Ativos")

        st.divider()

        # TABELA
        st.subheader("📋 Relatório de Transações (Tempo Real)")
        st.dataframe(df_vendas, use_container_width=True)
    else:
        st.info("O banco de dados está vazio. Ligue os robôs na InfinitePay e PicPay!")
