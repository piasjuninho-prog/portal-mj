import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ Soluções", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função Mestra para converter as datas do robô (InfinitePay e PicPay)
def limpar_e_converter_data(data_str):
    try:
        if not data_str: return None
        d = str(data_str).split(' •')[0].replace(',', '').strip()
        meses = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06',
                 'Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}
        if "/" in d:
            return pd.to_datetime(d, format='%d/%m/%Y', errors='coerce')
        for pt, num in meses.items():
            if pt in d:
                d = d.replace(pt, num)
                break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except:
        return None

# --- SISTEMA DE LOGIN ---
if 'perfil' not in st.session_state:
    st.session_state.perfil = None

if st.session_state.perfil is None:
    st.title("🔑 Portal MJ Soluções - Acesso")
    u = st.text_input("Usuário (Nome no Excel)").upper().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"
            st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D", "MJ PICPAY CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"
            st.session_state.usuario = u
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos.")
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])
    if menu == "🚪 Sair":
        st.session_state.perfil = None
        st.rerun()

    try:
        # 1. Busca dados das Views
        df_v_raw = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
        df_e_raw = pd.DataFrame(conn.table("extrato_consolidado").select("*").execute().data)

        if not df_v_raw.empty:
            # Padroniza as datas
            df_v_raw['data_dt'] = df_v_raw['data_venda'].apply(limpar_e_converter_data)
            df_e_raw['data_dt'] = df_e_raw['data_hora'].apply(limpar_e_converter_data)

            # Filtro por Lojista
            if st.session_state.perfil == "admin":
                lista_lj = sorted([str(x) for x in df_v_raw['lojista'].unique()])
                opcoes = ["TODOS OS CLIENTES"] + lista_lj
                escolha_lj = st.sidebar.selectbox("Filtrar Visão por Lojista:", options=opcoes)
                if escolha_lj == "TODOS OS CLIENTES":
                    df_v_user = df_v_raw.copy()
                    df_e_user = df_e_raw.copy()
                else:
                    df_v_user = df_v_raw[df_v_raw['lojista'] == escolha_lj].copy()
                    df_e_user = df_e_raw[df_e_raw['lojista'] == escolha_lj].copy()
            else:
                df_v_user = df_v_raw[df_v_raw['lojista'] == st.session_state.usuario].copy()
                df_e_user = df_e_raw[df_e_raw['lojista'] == st.session_state.usuario].copy()

            # --- FILTROS DE DATA (SIDEBAR) ---
            st.sidebar.divider()
            d_ini = st.sidebar.date_input("Início", df_v_raw['data_dt'].min().date())
            d_fim = st.sidebar.date_input("Fim", df_v_raw['data_dt'].max().date())
            tipo_filtro = st.sidebar.segmented_control("Ver Lançamentos:", ["Todos", "Entrada", "Saída"], default="Todos")

            # Aplica filtros de data
            df_v = df_v_user[(df_v_user['data_dt'].dt.date >= d_ini) & (df_v_user['data_dt'].dt.date <= d_fim)].copy()
            df_e_periodo = df_e_user[(df_e_user['data_dt'].dt.date >= d_ini) & (df_e_user['data_dt'].dt.date <= d_fim)].copy()

            # --- TELAS ---

            if menu == "🏠 Home":
                st.title("🏠 Visão Geral")
                saldo_total = df_e_user['valor'].sum()
                bruto_periodo = df_v['bruto'].sum()
                c1, c2 = st.columns(2)
                c1.metric("Saldo Total na Conta", f"R$ {saldo_total:,.2f}")
                c2.metric("Vendas Brutas (Período)", f"R$ {bruto_periodo:,.2f}")

            elif menu == "🏦 Seu banco":
                st.title("🏦 Seu extrato")
                saldo_total = df_e_user['valor'].sum()
                entradas = df_e_periodo[df_e_periodo['tipo'] == 'entrada']['valor'].sum()
                saidas = abs(df_e_periodo[df_e_periodo['tipo'] == 'saida']['valor'].sum())

                m1, m2, m3 = st.columns(3)
                m1.metric("Saldo Disponível", f"R$ {saldo_total:,.2f}")
                m2.metric("Entradas no Período", f"R$ {entradas:,.2f}")
                m3.metric("Saídas no Período", f"R$ {saidas:,.2f}")
                st.divider()

                # Lista de lançamentos
                df_e_exibir = df_e_periodo
                if tipo_filtro == "Entrada": df_e_exibir = df_e_periodo[df_e_periodo['tipo'] == 'entrada']
                elif tipo_filtro == "Saída": df_e_exibir = df_e_periodo[df_e_periodo['tipo'] == 'saida']

                if not df_e_exibir.empty:
                    for _, row in df_e_exibir.iloc[::-1].iterrows():
                        ca, cb, cc = st.columns([0.5, 4, 1.5])
                        icon = "🟢" if row['tipo'] == 'entrada' else "💸"
                        with ca: st.write(icon)
                        with cb: 
                            st.write(f"**{row['descricao']}**")
                            st.write(f"<span style='color:gray; font-size:12px;'>{row['data_hora']}</span>", unsafe_allow_html=True)
                        with cc:
                            cor = "green" if row['tipo'] == 'entrada' else "red"
                            simb = "+" if row['tipo'] == 'entrada' else ""
                            st.write(f"<p style='color:{cor}; font-weight:bold; text-align:right;'>{simb} R$ {abs(row['valor']):,.2f}</p>", unsafe_allow_html=True)
                        st.divider()
                else: st.info("Sem lançamentos no período.")

            elif menu == "🛒 Suas vendas":
                st.title("🛒 Detalhamento de Vendas")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Bruto no Período", f"R$ {df_v['bruto'].sum():,.2f}")
                m2.metric("Líquido no Período", f"R$ {df_v['liquido_cliente'].sum():,.2f}")
                m3.metric("Quantidade", f"{len(df_v)} vendas")

                if st.session_state.perfil == "admin":
                    st.info("💡 Visão Admin: Lucro MJ (Spread)")
                    m4, m5 = st.columns(2)
                    m4.metric("Seu Lucro (R$)", f"R$ {df_v['spread_rs'].sum():,.2f}")
                    m5.metric("Média Spread (%)", f"{(df_v['spread_percentual'].mean()*100):,.2f}%")

                st.write("---")
                exibir_v = df_v[['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].copy()
                exibir_v['taxa_cliente'] = (exibir_v['taxa_cliente'] * 100).map('{:.2f}%'.format)
                exibir_v.columns = ['Data', 'Bandeira', 'Plano', 'Valor Bruto', 'Sua Taxa', 'Valor Líquido']
                st.dataframe(exibir_v, use_container_width=True)

        else: st.info("Aguardando sincronização de vendas...")

    except Exception as e: st.error(f"Erro: {e}")
