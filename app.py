import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# Layout Estilo Bank
st.set_page_config(page_title="Portal MJ - Conta Digital", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função para converter a data do robô (Tratando meses PT-BR)
def converter_data(data_str):
    try:
        if not data_str: return None
        d = str(data_str).split(' •')[0].replace(',', '').strip()
        meses = {'Jan': '01', 'Fev': '02', 'Mar': '03', 'Abr': '04', 'Mai': '05', 'Jun': '06','Jul': '07', 'Ago': '08', 'Set': '09', 'Out': '10', 'Nov': '11', 'Dez': '12'}
        if "/" in d: return pd.to_datetime(d, format='%d/%m/%Y', errors='coerce')
        for pt, num in meses.items():
            if pt in d: d = d.replace(pt, num); break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except: return None

# --- SISTEMA DE LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None

if st.session_state.perfil is None:
    st.title("🏦 Portal MJ - Conta Digital")
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Acessar Conta"):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D", "MJ PICPAY CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"; st.session_state.usuario = u
            st.rerun()
        else: st.error("Dados de acesso inválidos.")
else:
    # --- INTERFACE LOGADA ---
    st.sidebar.markdown(f"### 👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("MENU PRINCIPAL", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])

    if menu == "🚪 Sair":
        st.session_state.perfil = None; st.rerun()

    try:
        # Busca dados de Vendas e Pix
        df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
        df_p = pd.DataFrame(conn.table("transacoes_pix").select("*").execute().data)

        # Filtro de Usuário
        if st.session_state.perfil == "admin":
            st.sidebar.divider()
            lista_lojistas = ["TODOS"] + sorted([str(x) for x in df_v['lojista'].unique()])
            escolha = st.sidebar.selectbox("Filtrar Lojista:", lista_lojistas)
            v_c_full = df_v.copy() if escolha == "TODOS" else df_v[df_v['lojista'] == escolha]
            pix_f = df_p.copy() if escolha == "TODOS" else df_p[df_p['origem'] == escolha]
        else:
            v_c_full = df_v[df_v['lojista'] == st.session_state.usuario].copy()
            pix_f = df_p[df_p['origem'] == st.session_state.usuario].copy() if not df_p.empty else pd.DataFrame()

        # --- CÁLCULO DE SALDO VIRTUAL ---
        total_entradas = v_c_full['liquido_cliente'].sum() if not v_c_full.empty else 0
        total_saidas = pix_f['valor'].sum() if not pix_f.empty else 0
        saldo_disponivel = total_entradas - total_saidas

        # --- TELAS ---
        if menu == "🏠 Home":
            st.title("🏠 Bem-vindo ao seu Portal")
            c1, c2, c3 = st.columns(3)
            c1.metric("Saldo para Pix", f"R$ {saldo_disponivel:,.2f}")
            c2.metric("Total Líquido Recebido", f"R$ {total_entradas:,.2f}")
            c3.metric("Bruto Vendido", f"R$ {v_c_full['bruto'].sum():,.2f}")

        elif menu == "🏦 Seu banco":
            st.title("🏦 Sua Conta Digital")
            st.markdown(f"## Saldo Disponível: **R$ {saldo_disponivel:,.2f}**")
            st.divider()

            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.subheader("💸 Realizar Pix")
                with st.form("form_pix"):
                    favorecido = st.text_input("Nome do Recebedor")
                    chave = st.text_input("Chave Pix")
                    valor = st.number_input("Valor (R$)", min_value=0.0, max_value=float(saldo_disponivel) if saldo_disponivel > 0 else 0.0)
                    if st.form_submit_button("CONFIRMAR ENVIO"):
                        if valor > 0 and valor <= saldo_disponivel:
                            dados_pix = {"origem": st.session_state.usuario, "destino": favorecido, "chave_pix": chave, "valor": valor}
                            conn.table("transacoes_pix").insert(dados_pix).execute()
                            st.success("Pix enviado com sucesso!")
                            st.rerun()
                        else: st.error("Saldo insuficiente.")

            with col_b:
                st.subheader("📜 Histórico de Transferências")
                if not pix_f.empty:
                    pix_f['Data'] = pd.to_datetime(pix_f['created_at']).dt.tz_convert('America/Sao_Paulo').dt.strftime('%d/%m/%Y %H:%M')
                    st.dataframe(pix_f[['Data', 'destino', 'valor']], use_container_width=True)
                else: st.info("Nenhum Pix enviado ainda.")

        elif menu == "🛒 Suas vendas":
            st.title("🛒 Extrato de Vendas")
            df_v_limpo = v_c_full.copy()
            df_v_limpo['data_dt'] = df_v_limpo['data_venda'].apply(converter_data)
            df_v_limpo = df_v_limpo.dropna(subset=['data_dt'])
            
            # Filtro Data
            st.sidebar.subheader("📅 Período")
            data_ini = st.sidebar.date_input("Início", df_v_limpo['data_dt'].min().date())
            data_fim = st.sidebar.date_input("Fim", df_v_limpo['data_dt'].max().date())
            v_final = df_v_limpo[(df_v_limpo['data_dt'].dt.date >= data_ini) & (df_v_limpo['data_dt'].dt.date <= data_fim)]

            m1, m2, m3 = st.columns(3)
            m1.metric("Bruto no Período", f"R$ {v_final['bruto'].sum():,.2f}")
            m2.metric("Vendas", len(v_final))
            m3.metric("Líquido", f"R$ {v_final['liquido_cliente'].sum():,.2f}")

            st.dataframe(v_final[['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']], use_container_width=True)

    except Exception as e: st.error(f"Erro: {e}")
