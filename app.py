import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

st.set_page_config(page_title="Portal MJ Soluções", layout="wide")

# --- CONEXÃO SEGURA ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função de Data Robusta (Entende PicPay e InfinitePay)
def converter_data(data_str):
    try:
        if not data_str: return None
        data_str = str(data_str).strip()
        # Caso 1: Formato PicPay (01/04/2026)
        if "/" in data_str and "•" not in data_str:
            return pd.to_datetime(data_str, format='%d/%m/%Y', errors='coerce')
        # Caso 2: Formato InfinitePay (01 Abr, 2026 • 10:57)
        d = data_str.split(' •')[0].replace(',', '').strip()
        meses = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06','Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}
        for pt, num in meses.items():
            if pt in d: d = d.replace(pt, num); break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except: return None

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
        else: st.error("Acesso negado.")
        st.rerun()
else:
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    try:
        # Busca dados e limpa lojistas nulos para não dar erro de ordenação
        df = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
        df['lojista'] = df['lojista'].fillna("NÃO IDENTIFICADO")

        if not df.empty:
            df['data_dt'] = df['data_venda'].apply(converter_data)
            df = df.dropna(subset=['data_dt'])

            # --- FILTROS ---
            if st.session_state.perfil == "admin":
                st.title("👨‍✈️ Painel Administrativo")
                # CORREÇÃO: Garante que todos os nomes de lojista sejam STRINGS antes de ordenar
                lista_lj = sorted([str(x) for x in df['lojista'].unique()])
                opcoes = ["TODOS OS CLIENTES"] + lista_lj
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

            # --- MÉTRICAS ---
            cols = st.columns(4)
            cols[0].metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}")
            cols[1].metric("Líquido Cliente", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
            
            if st.session_state.perfil == "admin":
                cols[2].metric("Seu Lucro (Spread)", f"R$ {v_c['spread_rs'].sum():,.2f}")
                cols[3].metric("Qtd Vendas", len(v_c))
            else:
                cols[2].metric("Qtd Vendas", len(v_c))

            st.write("---")
            # Tabela (Exibe o que for pertinente ao perfil)
            cols_show = ['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']
            if st.session_state.perfil == "admin": cols_show.insert(1, 'lojista')
            
            st.dataframe(v_c[cols_show], use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar dados. Verifique se o robô sincronizou corretamente. Erro: {e}")
