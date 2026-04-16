import streamlit as st
import pandas as pd
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh

# 1. Configuração da Página
st.set_page_config(page_title="Painel Geral MJ", layout="wide", page_icon="📊")

# 2. Gerenciamento de Login
if "logado" not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🔐 Acesso Administrativo</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        usuario = st.text_input("Usuário", key="user")
        senha = st.text_input("Senha", type="password", key="pass")
        if st.button("ACESSAR PAINEL", use_container_width=True):
            if usuario == "admin" and senha == "admin123":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

# --- ÁREA DO DASHBOARD ---
else:
    st_autorefresh(interval=30000, key="datarefresh")

    st.sidebar.title("MENU MJ")
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # --- CONFIGURAÇÃO SUPABASE ---
    URL_SB = "https://oiuyklgtcazbtuvwmelv.supabase.co"
    KEY_SB = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" # COLOQUE SUA KEY REAL AQUI

    @st.cache_resource
    def conectar():
        return create_client(URL_SB, KEY_SB)

    def carregar_e_processar_dados():
        try:
            sb = conectar()
            # 1. Puxa as vendas
            res_vendas = sb.table("vendas").select("*").execute()
            df_v = pd.DataFrame(res_vendas.data)
            
            # 2. Puxa as taxas que você me mostrou no print
            res_taxas = sb.table("taxas_clientes").select("*").execute()
            df_t = pd.DataFrame(res_taxas.data)

            if df_v.empty:
                return pd.DataFrame()

            # Limpeza básica de espaços e letras maiúsculas para o cruzamento não falhar
            for df in [df_v, df_t]:
                for col in ['ns', 'bandeira']:
                    if col in df.columns:
                        df[col] = df[col].astype(str).str.strip().str.lower()
            
            # No df_v a coluna chama 'plano', no df_t chama 'meio'
            df_v['plano'] = df_v['plano'].astype(str).str.strip().str.lower()
            df_t['meio'] = df_t['meio'].astype(str).str.strip().str.lower()

            # --- O CASAMENTO (MERGE) ---
            # Cruzamos a venda com a taxa baseada em NS + BANDEIRA + PLANO
            df_final = pd.merge(
                df_v, 
                df_t[['ns', 'bandeira', 'meio', 'taxa_decimal', 'cliente']], 
                left_on=['ns', 'bandeira', 'plano'], 
                right_on=['ns', 'bandeira', 'meio'], 
                how='left'
            )

            # 3. Cálculos Financeiros
            df_final['bruto'] = pd.to_numeric(df_final['bruto'], errors='coerce').fillna(0)
            df_final['taxa_decimal'] = pd.to_numeric(df_final['taxa_decimal'], errors='coerce').fillna(0)
            
            # Líquido do Cliente
            df_final['liquido_esperado'] = df_final['bruto'] * (1 - df_final['taxa_decimal'])
            
            # Seu Lucro (Spread) 
            # Como não temos a tabela de custo custo aqui ainda, vou calcular 
            # o spread como a taxa total por enquanto (ou você pode subtrair o custo se souber)
            df_final['seu_lucro'] = df_final['bruto'] * df_final['taxa_decimal'] 

            # Substitui o nome do lojista pelo nome oficial da tabela de taxas (se encontrar)
            df_final['lojista'] = df_final['cliente'].fillna(df_final['lojista'])
            
            return df_final
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
            return pd.DataFrame()

    df_completo = carregar_e_processar_dados()

    st.title("📊 Dashboard MJ Soluções")

    if not df_completo.empty:
        # Filtros na Sidebar
        st.sidebar.divider()
        lista_lojistas = sorted([x for x in df_completo['lojista'].unique() if str(x) != 'nan'])
        selecionados = st.sidebar.multiselect("Filtrar Lojistas:", options=lista_lojistas, default=lista_lojistas)
        
        df_filtrado = df_completo[df_completo['lojista'].isin(selecionados)]

        # --- MÉTRICAS ---
        c1, c2, c3, c4 = st.columns(4)
        total_bruto = df_filtrado['bruto'].sum()
        total_liq = df_filtrado['liquido_esperado'].sum()
        total_vendas = len(df_filtrado)
        total_lucro = df_filtrado['seu_lucro'].sum()

        c1.metric("Bruto Total", f"R$ {total_bruto:,.2f}")
        c2.metric("Líquido Esperado", f"R$ {total_liq:,.2f}")
        c3.metric("Qtd Vendas", total_vendas)
        c4.metric("Seu Lucro (Spread)", f"R$ {total_lucro:,.2f}")

        st.divider()

        # --- TABELA ---
        st.subheader("📋 Relatório de Transações")
        # Seleciona apenas as colunas principais para não ficar gigante
        cols_mostrar = ['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'liquido_esperado', 'taxa_decimal']
        st.dataframe(df_filtrado[cols_mostrar].sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Aguardando vendas...")

    st.caption("Atualização automática ativa (30s)")
