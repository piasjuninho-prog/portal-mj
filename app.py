import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Portal MJ Soluções", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = st.secrets["https://oiuyklgtcazbtuvwmelv.supabase.co"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"]
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

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
    if st.button("Entrar", use_container_width=True):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D", "MJ PICPAY CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"; st.session_state.usuario = u
            st.rerun()
        else: st.error("❌ Usuário ou senha incorretos.")
else:
    # --- MENU LATERAL ---
    opcoes_menu = ["🏠 Home", "🛒 Suas vendas"]
    if st.session_state.perfil == "admin":
        opcoes_menu.append("⚙️ Administração")
    opcoes_menu.append("🚪 Sair")

    st.sidebar.title(f"👤 {st.session_state.usuario}")
    st.sidebar.caption(f"🕒 Sincronizado: {datetime.now().strftime('%H:%M:%S')}")
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes_menu)
    
    if menu == "🚪 Sair": 
        st.session_state.perfil = None
        st.rerun()

    # --- ABA: ADMINISTRAÇÃO (APENAS CADASTRO INDIVIDUAL) ---
    if menu == "⚙️ Administração":
        st.title("⚙️ Cadastrar Taxa Individual")
        st.write("Insira as informações abaixo para cadastrar a taxa específica de um cliente.")
        
        with st.form("form_nova_taxa", clear_on_submit=True):
            col1, col2 = st.columns(2)
            novo_cliente = col1.text_input("Nome do Cliente (Ex: MJ INFINITE...)")
            novo_ns = col2.text_input("Número de Série (NS) ou Terminal")
            
            col3, col4, col5 = st.columns(3)
            nova_bandeira = col3.selectbox("Bandeira", ["mastercard", "visa", "elo", "amex", "hipercard"])
            novo_meio = col4.text_input("Plano (Ex: em 12x, à vista, débito)")
            nova_taxa = col5.number_input("Taxa Decimal (Ex: 0.1019 para 10.19%)", format="%.4f")
            
            if st.form_submit_button("✅ Salvar Novo Cadastro"):
                if novo_cliente and novo_ns and novo_meio:
                    conn.table("taxas_clientes").insert({
                        "cliente": novo_cliente.upper().strip(), 
                        "ns": novo_ns.strip(), 
                        "bandeira": nova_bandeira, 
                        "meio": novo_meio.lower().strip(), 
                        "taxa_decimal": nova_taxa
                    }).execute()
                    st.success(f"Sucesso! Taxa cadastrada para o cliente {novo_cliente.upper()}.")
                    st.cache_data.clear() # Limpa o cache para as novas vendas pegarem a taxa
                else:
                    st.error("Por favor, preencha todos os campos obrigatórios.")

    # --- ABA: HOME / VENDAS ---
    elif menu in ["🏠 Home", "🛒 Suas vendas"]:
        st_autorefresh(interval=30000, key="datarefresh")
        try:
            df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            
            if not df_v.empty:
                df_v = df_v[df_v['lojista'].astype(str).str.lower() != 'nan'].copy()
                df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
                df_v = df_v.dropna(subset=['data_dt'])

                if st.session_state.perfil == "admin":
                    st.title("👨‍✈️ Painel Geral MJ")
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

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}")
                m2.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
                m3.metric("Qtd Vendas", len(v_c))
                if st.session_state.perfil == "admin":
                    m4.metric("Seu Lucro (R$)", f"R$ {v_c['spread_rs'].sum():,.2f}")

                st.write("---")
                st.subheader("📋 Relatório de Transações")
                st.dataframe(v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)

        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções Comercial v4.1")
