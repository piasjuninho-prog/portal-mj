import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# Configuração visual do Portal
st.set_page_config(page_title="Portal MJ Soluções", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO SEGURA ---
SUPABASE_URL = st.secrets["supabase"]["https://oiuyklgtcazbtuvwmelv.supabase.co"]
SUPABASE_KEY = st.secrets["supabase"]["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"]

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função para converter a data do robô (Traduzindo meses PT-BR)
def converter_data(data_str):
    try:
        if not data_str: return None
        d = data_str.split(' •')[0].replace(',', '').strip()
        meses = {
            'Jan': '01', 'Fev': '02', 'Mar': '03', 'Abr': '04', 'Mai': '05', 'Jun': '06',
            'Jul': '07', 'Ago': '08', 'Set': '09', 'Out': '10', 'Nov': '11', 'Dez': '12'
        }
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
    st.title("🔑 Portal MJ - Acesso")
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"
            st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"
            st.session_state.usuario = u
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos.")
else:
    # --- MENU LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Home", "🏦 Seu banco", "🛒 Suas vendas", "🚪 Sair"])

    if menu == "🚪 Sair":
        st.session_state.perfil = None
        st.rerun()

    try:
        # Busca dados do banco
        df = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
        df_extrato = pd.DataFrame(conn.table("extrato_consolidado").select("*").execute().data)

        if not df.empty:
            # Tratamento de Data
            df['data_dt'] = df['data_venda'].apply(converter_data)
            df = df.dropna(subset=['data_dt'])

            # --- FILTRO DE VISÃO (ADMIN vs CLIENTE) ---
            if st.session_state.perfil == "admin":
                st.title("👨‍✈️ Painel Geral MJ (Administrador)")
                lista_lojistas = ["TODOS OS CLIENTES"] + list(df['lojista'].unique())
                # Correção na linha abaixo:
                escolha = st.sidebar.selectbox("Visualizar Lojista:", options=lista_lojistas)
                
                if escolha == "TODOS OS CLIENTES":
                    v_c_full = df.copy()
                    extrato_f = df_extrato.copy() if not df_extrato.empty else pd.DataFrame()
                else:
                    v_c_full = df[df['lojista'] == escolha].copy()
                    extrato_f = df_extrato[df_extrato['lojista'] == escolha].copy() if not df_extrato.empty else pd.DataFrame()
            else:
                st.title(f"🏠 Painel: {st.session_state.usuario}")
                # FILTRO EXATO: O cliente só vê o que for IDÊNTICO ao nome dele
                v_c_full = df[df['lojista'] == st.session_state.usuario].copy()
                extrato_f = df_extrato[df_extrato['lojista'] == st.session_state.usuario].copy() if not df_extrato.empty else pd.DataFrame()

            # --- FILTRO DE DATA ---
            st.sidebar.divider()
            st.sidebar.subheader("📅 Filtrar Período")
            data_ini = st.sidebar.date_input("Início", v_c_full['data_dt'].min().date())
            data_fim = st.sidebar.date_input("Fim", v_c_full['data_dt'].max().date())
            
            v_c = v_c_full[(v_c_full['data_dt'].dt.date >= data_ini) & (v_c_full['data_dt'].dt.date <= data_fim)]

            # --- TELAS ---
            if menu == "🏠 Home":
                saldo = extrato_f['valor'].sum() if not extrato_f.empty else 0
                c1, c2 = st.columns(2)
                c1.metric("Saldo Disponível", f"R$ {saldo:,.2f}")
                c2.metric("Bruto Total Vendido", f"R$ {v_c['bruto'].sum():,.2f}")
                st.divider()

            elif menu == "🏦 Seu banco":
                saldo = extrato_f['valor'].sum() if not extrato_f.empty else 0
                st.header(f"Saldo na Conta: R$ {saldo:,.2f}")
                col1, col2 = st.columns([1, 2])
                with col1:
                    with st.form("pix"):
                        st.write("💸 Enviar Pix")
                        dest = st.text_input("Nome")
                        chave = st.text_input("Chave Pix")
                        val = st.number_input("Valor", min_value=0.0, max_value=float(saldo) if saldo > 0 else 0.0)
                        if st.form_submit_button("Confirmar"):
                            if val > 0:
                                novo = {"origem": st.session_state.usuario, "destino": dest, "chave_pix": chave, "valor": val}
                                conn.table("transacoes_pix").insert(novo).execute()
                                st.rerun()
                with col2:
                    st.write("🕒 Lançamentos Recentes")
                    if not extrato_f.empty:
                        extrato_f = extrato_f.iloc[::-1]
                        for _, row in extrato_f.iterrows():
                            cor = "green" if row['tipo'] == 'entrada' else "black"
                            with st.container():
                                cx, cy = st.columns([3, 1])
                                cx.write(f"**{row['descricao']}**\n\n{row['data_hora']}")
                                cy.write(f"<p style='color:{cor}; font-weight:bold; text-align:right;'>R$ {row['valor']:,.2f}</p>", unsafe_allow_html=True)
                                st.divider()
                    else: st.write("Nenhuma movimentação.")

            elif menu == "🛒 Suas vendas":
                c1, c2, c3 = st.columns(3)
                c1.metric("Bruto no Período", f"R$ {v_c['bruto'].sum():,.2f}")
                c2.metric("Qtd de Vendas", len(v_c))
                c3.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}")

                if st.session_state.perfil == "admin":
                    st.info("💡 Visão Admin: Spread e Lucro")
                    m4, m5 = st.columns(2)
                    m4.metric("Seu Lucro MJ (R$)", f"R$ {v_c['spread_rs'].sum():,.2f}")
                    m5.metric("Spread Médio (%)", f"{(v_c['spread_percentual'].mean() * 100):,.2f}%")

                st.write("---")
                if st.session_state.perfil == "admin":
                    exibir = v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'taxa_custo', 'spread_percentual', 'spread_rs', 'liquido_cliente']].copy()
                    exibir['taxa_cliente'] = (exibir['taxa_cliente'] * 100).map('{:.2f}%'.format)
                    exibir['taxa_custo'] = (exibir['taxa_custo'] * 100).map('{:.2f}%'.format)
                    exibir['spread_percentual'] = (exibir['spread_percentual'] * 100).map('{:.2f}%'.format)
                else:
                    exibir = v_c[['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].copy()
                    exibir['taxa_cliente'] = (exibir['taxa_cliente'] * 100).map('{:.2f}%'.format)
                
                st.dataframe(exibir, use_container_width=True)

        else: st.info("Nenhum dado encontrado.")
    except Exception as e: st.error(f"Erro: {e}")
