import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date

# Configuração visual
st.set_page_config(page_title="Portal MJ Soluções", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função Mestra para converter qualquer data do sistema para objeto real do Python
def limpar_e_converter_data(data_str):
    try:
        if not data_str: return None
        d = str(data_str).split(' •')[0].replace(',', '').strip()
        # Dicionário de meses para conversão
        meses = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
                 'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}
        # Se for formato DD/MM/YYYY (PicPay)
        if "/" in d:
            return pd.to_datetime(d, format='%d/%m/%Y', errors='coerce')
        # Se for formato DD Mes YYYY (InfinitePay)
        for pt, num in meses.items():
            if pt in d:
                d = d.replace(pt, num)
                break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except:
        return None

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None

if st.session_state.perfil is None:
    st.title("🔑 Portal MJ - Acesso")
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D", "MJ PICPAY CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"; st.session_state.usuario = u
            st.rerun()
        else: st.error("Acesso negado.")
else:
    # --- BARRA LATERAL (MENU E FILTROS) ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])
    
    if menu == "🚪 Sair":
        st.session_state.perfil = None
        st.rerun()

    try:
        # 1. Busca todos os dados do banco
        df_v_raw = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
        df_e_raw = pd.DataFrame(conn.table("extrato_consolidado").select("*").execute().data)

        if not df_v_raw.empty:
            # 2. Padroniza as datas em ambos os DataFrames
            df_v_raw['data_dt'] = df_v_raw['data_venda'].apply(limpar_e_converter_data)
            df_e_raw['data_dt'] = df_e_raw['data_hora'].apply(limpar_e_converter_data)

            # 3. Filtro de Usuário (Lojista)
            if st.session_state.perfil == "admin":
                lista_lj = ["TODOS OS CLIENTES"] + sorted([str(x) for x in df_v_raw['lojista'].unique()])
                escolha_lj = st.sidebar.selectbox("Lojista:", lista_lj)
                if escolha_lj == "TODOS OS CLIENTES":
                    df_v_user = df_v_raw.copy()
                    df_e_user = df_e_raw.copy()
                else:
                    df_v_user = df_v_raw[df_v_raw['lojista'] == escolha_lj].copy()
                    df_e_user = df_e_raw[df_e_raw['lojista'] == escolha_lj].copy()
            else:
                df_v_user = df_v_raw[df_v_raw['lojista'] == st.session_state.usuario].copy()
                df_e_user = df_e_raw[df_e_raw['lojista'] == st.session_state.usuario].copy()

            # --- 4. FILTRO DE DATA GLOBAL (SIDEBAR) ---
            st.sidebar.divider()
            st.sidebar.subheader("📅 Filtrar Período")
            
            # Pega a data mínima e máxima disponível no banco
            min_d = df_v_raw['data_dt'].min().date() if not df_v_raw['data_dt'].isnull().all() else date.today()
            max_d = df_v_raw['data_dt'].max().date() if not df_v_raw['data_dt'].isnull().all() else date.today()
            
            d_ini = st.sidebar.date_input("De:", min_d)
            d_fim = st.sidebar.date_input("Até:", max_d)

            # Aplica o filtro de data nos dois conjuntos de dados
            df_v = df_v_user[(df_v_user['data_dt'].dt.date >= d_ini) & (df_v_user['data_dt'].dt.date <= d_fim)].copy()
            df_e = df_e_user[(df_e_user['data_dt'].dt.date >= d_ini) & (df_e_user['data_dt'].dt.date <= d_fim)].copy()

            # --- RENDERIZAÇÃO DAS TELAS ---

            if menu == "🏠 Home":
                st.title("🏠 Visão Geral")
                saldo_total = df_e_user['valor'].sum() # Saldo é sempre o acumulado total
                bruto_periodo = df_v['bruto'].sum()
                
                c1, c2 = st.columns(2)
                c1.metric("Saldo Atual na Conta", f"R$ {saldo_total:,.2f}")
                c2.metric("Vendas no Período (Bruto)", f"R$ {bruto_periodo:,.2f}")

            elif menu == "🏦 Seu banco":
                st.title("🏦 Extrato da Conta")
                saldo_total = df_e_user['valor'].sum()
                st.metric("Saldo disponível para Pix", f"R$ {saldo_total:,.2f}")
                
                st.write("---")
                st.subheader(f"🕒 Lançamentos: {d_ini.strftime('%d/%m/%y')} a {d_fim.strftime('%d/%m/%y')}")

                if not df_e.empty:
                    for _, row in df_e.iloc[::-1].iterrows():
                        col_icon, col_txt, col_val = st.columns([0.5, 4, 1.5])
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
                else: st.info("Nenhuma movimentação neste período.")

            elif menu == "🛒 Suas vendas":
                st.title("🛒 Detalhamento de Vendas")
                m1, m2, m3 = st.columns(3)
                m1.metric("Bruto no Período", f"R$ {df_v['bruto'].sum():,.2f}")
                m2.metric("Qtd Vendas", len(df_v))
                m3.metric("Líquido MJ", f"R$ {df_v['liquido_cliente'].sum():,.2f}")
                
                st.write("---")
                exibir_v = df_v[['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].copy()
                exibir_v['taxa_cliente'] = (exibir_v['taxa_cliente'] * 100).map('{:.2f}%'.format)
                st.dataframe(exibir_v, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
