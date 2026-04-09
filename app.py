import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

st.set_page_config(page_title="Portal MJ Soluções", layout="wide")

# --- CONEXÃO ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔑 Portal MJ - Acesso")
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "ADMIN" and p == "mj123": st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D", "MJ PICPAY CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"; st.session_state.usuario = u
        st.rerun()
else:
    # --- MENU LATERAL ---
    st.sidebar.title(f"Olá, {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    try:
        # Busca Extrato e Vendas
        df_extrato = pd.DataFrame(conn.table("extrato_consolidado").select("*").execute().data)
        df_vendas = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)

        # Filtro de Usuário
        if st.session_state.perfil != "admin":
            df_e = df_extrato[df_extrato['lojista'] == st.session_state.usuario].copy()
            df_v = df_vendas[df_vendas['lojista'] == st.session_state.usuario].copy()
        else:
            lj = st.sidebar.selectbox("Lojista (Admin):", ["TODOS"] + list(df_extrato['lojista'].unique()))
            df_e = df_extrato.copy() if lj == "TODOS" else df_extrato[df_extrato['lojista'] == lj]
            df_v = df_vendas.copy() if lj == "TODOS" else df_vendas[df_vendas['lojista'] == lj]

        # --- TELA: SEU BANCO (ESTILO INFINITEPAY) ---
        if menu == "🏦 Seu banco":
            st.title("🏦 Seu extrato")
            saldo = df_e['valor'].sum() if not df_e.empty else 0
            st.metric("Saldo disponível", f"R$ {saldo:,.2f}")
            
            st.write("---")
            st.subheader("🕒 Lançamentos")

            if not df_e.empty:
                # Inverte para os mais novos ficarem no topo
                for _, row in df_e.iloc[::-1].iterrows():
                    col_icon, col_txt, col_val = st.columns([0.5, 4, 1.5])
                    
                    # Ícone similar ao da InfinitePay
                    icon = "🟢" if row['tipo'] == 'entrada' else "💸"
                    
                    with col_icon: st.write(icon)
                    with col_txt:
                        st.write(f"**{row['descricao']}**")
                        st.write(f"<span style='color:gray; font-size:12px;'>{row['data_hora']}</span>", unsafe_allow_html=True)
                    with col_val:
                        cor = "green" if row['tipo'] == 'entrada' else "black"
                        simbolo = "+" if row['tipo'] == 'entrada' else ""
                        st.write(f"<p style='color:{cor}; font-weight:bold; text-align:right;'>{simbolo} R$ {abs(row['valor']):,.2f}</p>", unsafe_allow_html=True)
                    st.divider()
            else:
                st.info("Nenhuma movimentação na conta.")

        # --- TELA: SUAS VENDAS (MANTEMOS O DETALHAMENTO BRUTO/TAXA) ---
        elif menu == "🛒 Suas vendas":
            st.title("🛒 Suas vendas")
            m1, m2 = st.columns(2)
            m1.metric("Bruto Vendido", f"R$ {df_v['bruto'].sum():,.2f}")
            m2.metric("Qtd Vendas", len(df_v))
            st.write("---")
            st.dataframe(df_v[['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']], use_container_width=True)

    except Exception as e: st.error(f"Erro: {e}")
