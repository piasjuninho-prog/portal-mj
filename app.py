import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Portal MJ Soluções", layout="wide")

# --- CONEXÃO SEGURA ---
# O Streamlit vai ler essas chaves de um lugar secreto (Secrets)
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função para converter data
def converter_data(data_str):
    try:
        if not data_str: return None
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
        if u == "ADMIN" and p == "mj123": st.session_state.perfil = "admin"
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"; st.session_state.usuario = u
        else: st.error("Acesso negado.")
        st.rerun()
else:
    # --- MENU LATERAL ---
    st.sidebar.title(f"Olá, {st.session_state.usuario if 'usuario' in st.session_state else 'Admin'}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])

    if menu == "🚪 Sair":
        st.session_state.perfil = None
        st.rerun()

    try:
        # Busca dados unificados
        df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
        df_extrato = pd.DataFrame(conn.table("extrato_consolidado").select("*").execute().data)

        if st.session_state.perfil != "admin":
            df_v = df_v[df_v['lojista'].str.contains(st.session_state.usuario, case=False, na=False)].copy()
            df_extrato = df_extrato[df_extrato['lojista'] == st.session_state.usuario].copy()
        else:
            lj = st.sidebar.selectbox("Lojista (Admin):", ["TODOS"] + list(df_v['lojista'].unique()))
            if lj != "TODOS":
                df_v = df_v[df_v['lojista'] == lj]
                df_extrato = df_extrato[df_extrato['lojista'] == lj]

        # --- TELAS ---
        if menu == "🏠 Home":
            st.title("🏠 Visão Geral")
            saldo = df_extrato['valor'].sum() if not df_extrato.empty else 0
            c1, c2 = st.columns(2)
            c1.metric("Saldo na Conta", f"R$ {saldo:,.2f}")
            c2.metric("Bruto Total Vendido", f"R$ {df_v['bruto'].sum():,.2f}")

        elif menu == "🏦 Seu banco":
            st.title("🏦 Seu extrato")
            saldo = df_extrato['valor'].sum() if not df_extrato.empty else 0
            st.header(f"R$ {saldo:,.2f}")
            col1, col2 = st.columns([1, 2])
            with col1:
                with st.form("pix"):
                    st.write("💸 Enviar Pix")
                    dest = st.text_input("Nome")
                    chave = st.text_input("Chave Pix")
                    val = st.number_input("Valor", min_value=0.0, max_value=float(saldo) if saldo > 0 else 0.0)
                    if st.form_submit_button("Confirmar"):
                        if val > 0:
                            novo = {"origem": st.session_state.usuario if st.session_state.perfil=="cliente" else "ADMIN", "destino": dest, "chave_pix": chave, "valor": val}
                            conn.table("transacoes_pix").insert(novo).execute()
                            st.rerun()
            with col2:
                st.write("🕒 Lançamentos Recentes")
                if not df_extrato.empty:
                    # Inverte para mostrar os novos primeiro
                    df_extrato = df_extrato.iloc[::-1] 
                    for _, row in df_extrato.iterrows():
                        color = "green" if row['tipo'] == 'entrada' else "black"
                        with st.container():
                            ca, cb = st.columns([3, 1])
                            ca.write(f"**{row['descricao']}**\n\n{row['data_hora']}")
                            cb.write(f"<p style='color:{color}; font-weight:bold; text-align:right;'>R$ {row['valor']:,.2f}</p>", unsafe_allow_html=True)
                            st.divider()

        elif menu == "🛒 Suas vendas":
            st.title("🛒 Suas vendas")
            df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
            df_v = df_v.dropna(subset=['data_dt'])
            st.sidebar.divider()
            d_ini = st.sidebar.date_input("Início", df_v['data_dt'].min().date())
            d_fim = st.sidebar.date_input("Fim", df_v['data_dt'].max().date())
            v_c = df_v[(df_v['data_dt'].dt.date >= d_ini) & (df_v['data_dt'].dt.date <= d_fim)]
            m1, m2, m3 = st.columns(3)
            m1.metric("Bruto", f"R$ {v_c['bruto'].sum():,.2f}")
            m2.metric("Qtd", len(v_c))
            m3.metric("Líquido", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
            st.dataframe(v_c[['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']], use_container_width=True)

    except Exception as e: st.error(f"Erro: {e}")
