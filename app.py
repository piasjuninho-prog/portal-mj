import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

st.set_page_config(page_title="Sistema MJ - Gestão Admin", layout="wide")

# --- CONEXÃO SEGURA ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função de Data
def converter_data(data_str):
    try:
        d = data_str.split(' •')[0].replace(',', '').strip()
        meses = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06','Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}
        for pt, num in meses.items():
            if pt in d: d = d.replace(pt, num); break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except: return None

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔑 Login")
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "ADMIN" and p == "mj123": st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D"] and p == "12345": st.session_state.perfil = "cliente"; st.session_state.usuario = u
        else: st.error("Erro no login")
        st.rerun()
else:
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    try:
        # Busca dados da VIEW
        res = conn.table("dashboard_vendas").select("*").execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            df['data_dt'] = df['data_venda'].apply(converter_data)
            df = df.dropna(subset=['data_dt'])
            
            # --- FILTROS ---
            if st.session_state.perfil == "admin":
                st.title("👨‍✈️ Painel Admin")
                opcoes = ["TODOS OS CLIENTES"] + sorted(list(df['lojista'].unique()))
                escolha = st.sidebar.selectbox("Filtrar Visão:", options=opcoes)
                df_f = df.copy() if escolha == "TODOS OS CLIENTES" else df[df['lojista'] == escolha]
            else:
                st.title(f"🏠 Painel: {st.session_state.usuario}")
                df_f = df[df['lojista'] == st.session_state.usuario].copy()

            # Filtro Data
            st.sidebar.divider()
            d_ini = st.sidebar.date_input("Início", df_f['data_dt'].min().date())
            d_fim = st.sidebar.date_input("Fim", df_f['data_dt'].max().date())
            v_c = df_f[(df_f['data_dt'].dt.date >= d_ini) & (df_f['data_dt'].dt.date <= d_fim)]

            # --- MÉTRICAS DE TOPO (5 COLUNAS) ---
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}")
            m2.metric("Nº de Vendas", len(v_c)) # A QUANTIDADE VOLTOU!
            m3.metric("Líquido Clientes", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
            m4.metric("Seu Lucro (Spread)", f"R$ {v_c['spread_rs'].sum():,.2f}")
            m5.metric("Margem Média (%)", f"{(v_c['spread_percentual'].mean()*100):,.2f}%")

            st.write("---")

            # --- RESUMO POR CLIENTE (SÓ PARA ADMIN) ---
            if st.session_state.perfil == "admin" and escolha == "TODOS OS CLIENTES":
                st.subheader("📊 Resumo por Lojista")
                resumo = v_c.groupby('lojista').agg({'bruto': 'sum', 'spread_rs': 'sum', 'id': 'count'}).rename(columns={'id': 'Qtd Vendas', 'bruto': 'Faturamento', 'spread_rs': 'Seu Lucro'})
                st.table(resumo.style.format("R$ {:,.2f}"))

            # --- TABELA DETALHADA ---
            st.subheader("📑 Relatório Detalhado")
            if st.session_state.perfil == "admin":
                cols_exibir = ['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'taxa_custo', 'spread_rs', 'liquido_cliente']
            else:
                cols_exibir = ['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']
            
            st.dataframe(v_c[cols_exibir], use_container_width=True)

    except Exception as e:
        st.error(f"Erro: {e}")
