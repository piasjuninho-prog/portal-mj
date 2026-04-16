import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ Soluções", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função para converter data (InfinitePay e PicPay)
def converter_data(data_str):
    try:
        if not data_str: return None
        d = str(data_str).split(' •')[0].replace(',', '').strip()
        if "/" in d: return pd.to_datetime(d, format='%d/%m/%Y', errors='coerce')
        meses = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06','Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}
        for pt, num in meses.items():
            if pt in d: d = d.replace(pt, num); break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except: return None

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔑 Portal MJ Soluções - Login")
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D", "MJ PICPAY CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"; st.session_state.usuario = u
            st.rerun()
        else: st.error("❌ Usuário ou senha incorretos.")
else:
    # --- INTERFACE LOGADA ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    try:
        # 1. Busca dados
        df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
        
        if not df_v.empty:
            # 2. FILTRO DE SEGURANÇA: Remove qualquer erro de NS da lista de lojistas
            df_v = df_v[~df_v['lojista'].str.contains("NÃO", na=False)].copy()
            df_v = df_v[df_v['lojista'] != 'NÃO IDENTIFICADO'].copy()

            # 3. Tratamento de Datas
            df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
            df_v = df_v.dropna(subset=['data_dt'])

            # --- FILTROS ADMIN vs CLIENTE ---
            if st.session_state.perfil == "admin":
                st.title("👨‍✈️ Painel Geral MJ")
                # Menu limpo: Só mostra nomes de clientes reais
                lista_lj = sorted([str(x) for x in df_v['lojista'].unique() if x])
                escolha = st.sidebar.multiselect("Filtrar Lojistas:", options=lista_lj, default=lista_lj)
                v_c = df_v[df_v['lojista'].isin(escolha)].copy()
            else:
                st.title(f"🏠 Painel: {st.session_state.usuario}")
                v_c = df_v[df_v['lojista'] == st.session_state.usuario].copy()

            # Filtro Data
            st.sidebar.divider()
            d_ini = st.sidebar.date_input("Início", v_c['data_dt'].min().date())
            d_fim = st.sidebar.date_input("Fim", v_c['data_dt'].max().date())
            v_c = v_c[(v_c['data_dt'].dt.date >= d_ini) & (v_c['data_dt'].dt.date <= d_fim)]

            # --- MÉTRICAS ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}")
            m2.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
            m3.metric("Qtd Vendas", len(v_c))
            if st.session_state.perfil == "admin":
                m4.metric("Seu Lucro (R$)", f"R$ {v_c['spread_rs'].sum():,.2f}")

            st.write("---")
            # Exibe Tabela formatada
            exibir = v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].copy()
            exibir['taxa_cliente'] = (exibir['taxa_cliente'] * 100).map('{:.2f}%'.format)
            st.dataframe(exibir, use_container_width=True)

        else: st.info("Aguardando sincronização...")

    except Exception as e: st.error(f"Erro no sistema: {e}")
