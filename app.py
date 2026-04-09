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

# Função para converter data
def limpar_e_converter_data(data_str):
    try:
        if not data_str: return None
        d = str(data_str).split(' •')[0].replace(',', '').strip()
        meses = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06','Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}
        if "/" in d: return pd.to_datetime(d, format='%d/%m/%Y', errors='coerce')
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
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    try:
        # Busca dados
        df_v_raw = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
        df_e_raw = pd.DataFrame(conn.table("extrato_consolidado").select("*").execute().data)

        if not df_v_raw.empty:
            df_v_raw['data_dt'] = df_v_raw['data_venda'].apply(limpar_e_converter_data)
            df_e_raw['data_dt'] = df_e_raw['data_hora'].apply(limpar_e_converter_data)

            # Filtro de Usuário
            if st.session_state.perfil != "admin":
                df_v_user = df_v_raw[df_v_raw['lojista'] == st.session_state.usuario].copy()
                df_e_user = df_e_raw[df_e_raw['lojista'] == st.session_state.usuario].copy()
            else:
                lista_lj = ["TODOS"] + sorted([str(x) for x in df_v_raw['lojista'].unique()])
                esc_lj = st.sidebar.selectbox("Lojista:", lista_lj)
                df_v_user = df_v_raw.copy() if esc_lj == "TODOS" else df_v_raw[df_v_raw['lojista'] == esc_lj]
                df_e_user = df_e_raw.copy() if esc_lj == "TODOS" else df_e_raw[df_e_raw['lojista'] == esc_lj]

            # FILTRO DE DATA
            st.sidebar.divider()
            d_ini = st.sidebar.date_input("Início", df_v_raw['data_dt'].min().date())
            d_fim = st.sidebar.date_input("Fim", df_v_raw['data_dt'].max().date())
            
            # FILTRO DE TIPO (Igual InfinitePay)
            tipo_filtro = st.sidebar.segmented_control("Lançamentos de:", ["Todos", "Entrada", "Saída"], default="Todos")

            df_v = df_v_user[(df_v_user['data_dt'].dt.date >= d_ini) & (df_v_user['data_dt'].dt.date <= d_fim)].copy()
            df_e_periodo = df_e_user[(df_e_user['data_dt'].dt.date >= d_ini) & (df_e_user['data_dt'].dt.date <= d_fim)].copy()

            if menu == "🏠 Home":
                st.title("🏠 Visão Geral")
                saldo_total = df_e_user['valor'].sum()
                st.metric("Saldo Total na Conta", f"R$ {saldo_total:,.2f}")

            elif menu == "🏦 Seu banco":
                st.title("🏦 Seu extrato")
                
                # Cálculos de Entrada e Saída do Período
                entradas = df_e_periodo[df_e_periodo['tipo'] == 'entrada']['valor'].sum()
                saidas = abs(df_e_periodo[df_e_periodo['tipo'] == 'saida']['valor'].sum())
                saldo_total = df_e_user['valor'].sum()

                # Métricas de resumo (Sua resposta está aqui!)
                c1, c2, c3 = st.columns(3)
                c1.metric("Saldo Atual", f"R$ {saldo_total:,.2f}")
                c2.metric("Total Entradas (Período)", f"R$ {entradas:,.2f}", delta=f"+ {len(df_e_periodo[df_e_periodo['tipo']=='entrada'])} depósitos")
                c3.metric("Total Saídas (Período)", f"R$ {saidas:,.2f}", delta=f"- {len(df_e_periodo[df_e_periodo['tipo']=='saida'])} pix", delta_color="inverse")

                st.divider()
                
                # Aplica filtro de tipo no extrato
                if tipo_filtro == "Entrada":
                    df_e_exibir = df_e_periodo[df_e_periodo['tipo'] == 'entrada']
                elif tipo_filtro == "Saída":
                    df_e_exibir = df_e_periodo[df_e_periodo['tipo'] == 'saida']
                else:
                    df_e_exibir = df_e_periodo

                if not df_e_exibir.empty:
                    for _, row in df_e_exibir.iloc[::-1].iterrows():
                        col_icon, col_txt, col_val = st.columns([0.5, 4, 1.5])
                        icon = "🟢" if row['tipo'] == 'entrada' else "💸"
                        with col_icon: st.write(icon)
                        with col_txt:
                            st.write(f"**{row['descricao']}**")
                            st.write(f"<span style='color:gray; font-size:12px;'>{row['data_hora']}</span>", unsafe_allow_html=True)
                        with col_val:
                            cor = "green" if row['tipo'] == 'entrada' else "red"
                            simbolo = "+" if row['tipo'] == 'entrada' else ""
                            st.write(f"<p style='color:{cor}; font-weight:bold; text-align:right;'>{simbolo} R$ {abs(row['valor']):,.2f}</p>", unsafe_allow_html=True)
                        st.divider()
                else: st.info("Nenhuma movimentação para o filtro selecionado.")

            elif menu == "🛒 Suas vendas":
                st.title("🛒 Detalhamento")
                st.metric("Total Bruto no Período", f"R$ {df_v['bruto'].sum():,.2f}")
                st.dataframe(df_v[['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']], use_container_width=True)

    except Exception as e: st.error(f"Erro: {e}")
