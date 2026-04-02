import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# Configuração visual profissional (Fundo branco, menu lateral cinza)
st.set_page_config(page_title="Portal MJ Soluções", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO SEGURA (Secrets do Streamlit Cloud) ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função para converter a data do robô (Tratando meses PT-BR)
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
    st.title("🔑 Portal MJ - Acesso Restrito")
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
        # Busca dados brutos das VIEWs e Tabelas
        df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
        df_p = pd.DataFrame(conn.table("transacoes_pix").select("*").execute().data)
        df_extrato = pd.DataFrame(conn.table("extrato_consolidado").select("*").execute().data)

        # Filtro Global de Usuário
        if st.session_state.perfil != "admin":
            # Visão do Cliente: Vê apenas os seus dados
            df_v = df_v[df_v['lojista'].str.contains(st.session_state.usuario, case=False, na=False)].copy()
            df_extrato = df_extrato[df_extrato['lojista'] == st.session_state.usuario].copy()
        else:
            # Visão Admin: Pode filtrar por lojista na barra lateral
            lojistas_disponiveis = ["TODOS OS CLIENTES"] + list(df_v['lojista'].unique())
            escolha = st.sidebar.selectbox("Filtrar Visão por Lojista:", lojistas_disponiveis)
            if escolha != "TODOS OS CLIENTES":
                df_v = df_v[df_v['lojista'] == escolha]
                df_extrato = df_extrato[df_extrato['lojista'] == escolha]

        # Limpeza de Datas
        df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
        df_v = df_v.dropna(subset=['data_dt'])

        # --- TELA 1: HOME ---
        if menu == "🏠 Home":
            st.title("🏠 Visão Geral")
            saldo = df_extrato['valor'].sum() if not df_extrato.empty else 0
            c1, c2 = st.columns(2)
            c1.metric("Saldo Disponível", f"R$ {saldo:,.2f}")
            c2.metric("Total Vendido (Bruto)", f"R$ {df_v['bruto'].sum():,.2f}")
            st.divider()
            st.write("Dica: Use o menu lateral para ver seu extrato detalhado ou realizar transferências.")

        # --- TELA 2: SEU BANCO (CONTA VIRTUAL) ---
        elif menu == "🏦 Seu banco":
            st.title("🏦 Seu Banco")
            saldo = df_extrato['valor'].sum() if not df_extrato.empty else 0
            st.header(f"Saldo na Conta: R$ {saldo:,.2f}")

            col_pix1, col_pix2 = st.columns([1, 2])
            
            with col_pix1:
                with st.form("envio_pix"):
                    st.write("💸 Realizar Transferência")
                    favorecido = st.text_input("Nome do Favorecido")
                    chave = st.text_input("Chave Pix")
                    valor = st.number_input("Valor (R$)", min_value=0.0, max_value=float(saldo) if saldo > 0 else 0.0)
                    if st.form_submit_button("Confirmar Envio"):
                        if valor > 0:
                            novo_pix = {
                                "origem": st.session_state.usuario,
                                "destino": favorecido,
                                "chave_pix": chave,
                                "valor": valor
                            }
                            conn.table("transacoes_pix").insert(novo_pix).execute()
                            st.success("✅ Pix realizado!")
                            st.rerun()
                        else:
                            st.error("Valor inválido.")

            with col_pix2:
                st.write("🕒 Lançamentos Recentes")
                if not df_extrato.empty:
                    df_extrato = df_extrato.iloc[::-1] # Mostra os mais recentes no topo
                    for _, row in df_extrato.iterrows():
                        cor = "green" if row['tipo'] == 'entrada' else "black"
                        with st.container():
                            cx, cy = st.columns([3, 1])
                            cx.write(f"**{row['descricao']}**\n\n{row['data_hora']}")
                            cy.write(f"<p style='color:{cor}; font-weight:bold; text-align:right;'>R$ {row['valor']:,.2f}</p>", unsafe_allow_html=True)
                            st.divider()
                else:
                    st.write("Nenhuma movimentação encontrada.")

        # --- TELA 3: SUAS VENDAS (COM FILTRO DE DATA E SPREAD) ---
        elif menu == "🛒 Suas vendas":
            st.title("🛒 Detalhamento de Vendas")
            
            # Filtro de Calendário na Barra Lateral
            st.sidebar.divider()
            st.sidebar.subheader("📅 Filtrar Período")
            data_ini = st.sidebar.date_input("De:", df_v['data_dt'].min().date())
            data_fim = st.sidebar.date_input("Até:", df_v['data_dt'].max().date())
            
            v_c = df_v[(df_v['data_dt'].dt.date >= data_ini) & (df_v['data_dt'].dt.date <= data_fim)]

            # Métricas no topo da tela
            m1, m2, m3 = st.columns(3)
            m1.metric("Bruto no Período", f"R$ {v_c['bruto'].sum():,.2f}")
            m2.metric("Qtd de Vendas", len(v_c))
            m3.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}")

            # Visão exclusiva para o ADMIN (Spread)
            if st.session_state.perfil == "admin":
                st.info("💡 Visão de Administrador: Os campos abaixo não são visíveis para os clientes.")
                m4, m5 = st.columns(2)
                lucro_mj = v_c['spread_rs'].sum()
                perc_medio = (v_c['spread_percentual'].mean() * 100) if not v_c.empty else 0
                m4.metric("Seu Lucro MJ (Spread R$)", f"R$ {lucro_mj:,.2f}")
                m5.metric("Spread Médio (%)", f"{perc_medio:.2f}%")

            st.write("---")
            
            # Formatação da tabela para cada tipo de usuário
            if st.session_state.perfil == "admin":
                # Admin vê tudo
                exibir = v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'taxa_custo', 'spread_percentual', 'spread_rs', 'liquido_cliente']].copy()
                exibir['taxa_cliente'] = (exibir['taxa_cliente'] * 100).map('{:.2f}%'.format)
                exibir['taxa_custo'] = (exibir['taxa_custo'] * 100).map('{:.2f}%'.format)
                exibir['spread_percentual'] = (exibir['spread_percentual'] * 100).map('{:.2f}%'.format)
                exibir.columns = ['Data', 'Lojista', 'Bandeira', 'Plano', 'Bruto', 'Taxa Cli.', 'Sua Taxa (Custo)', 'Spread %', 'Seu Lucro (R$)', 'Líq. Cliente']
            else:
                # Cliente vê apenas o básico
                exibir = v_c[['data_venda', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].copy()
                exibir['taxa_cliente'] = (exibir['taxa_cliente'] * 100).map('{:.2f}%'.format)
                exibir.columns = ['Data', 'Bandeira', 'Plano', 'Valor Bruto', 'Taxa Aplicada', 'Valor Líquido']
            
            st.dataframe(exibir, use_container_width=True)

    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados. Verifique a aba de vendas e o banco de dados. Erro: {e}")
