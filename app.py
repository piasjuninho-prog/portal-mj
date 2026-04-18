import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configuração visual
st.set_page_config(page_title="Portal MJ Soluções", layout="wide", initial_sidebar_state="expanded")

# --- 1. CONEXÃO (COLE SEUS DADOS DENTRO DAS ASPAS) ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 

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

# --- 2. LOGIN ---
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
    # --- 3. MENU LATERAL ---
    opcoes = ["🏠 Home", "🛒 Suas vendas"]
    if st.session_state.perfil == "admin":
        opcoes.append("⚙️ Adicionar Taxas")
    opcoes.append("🚪 Sair")

    st.sidebar.title(f"👤 {st.session_state.usuario}")
    st.sidebar.caption(f"🕒 Sincronizado: {datetime.now().strftime('%H:%M:%S')}")
    
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 4. ABA: ADICIONAR TAXAS (INDIVIDUAL) ---
    if menu == "⚙️ Adicionar Taxas":
        st.title("➕ Cadastrar Nova Taxa por Cliente")
        st.write("Use este formulário para configurar as taxas de cada maquininha (NS).")
        
        with st.form("form_taxa"):
            c1, c2 = st.columns(2)
            nome_cli = c1.text_input("Nome do Cliente (Igual ao Robô)")
            ns_maquina = c2.text_input("Número de Série (NS)")
            
            c3, c4, c5 = st.columns(3)
            band = c3.selectbox("Bandeira", ["mastercard", "visa", "elo", "amex"])
            meio = c4.text_input("Plano (Ex: em 12x, à vista, débito)")
            valor_taxa = c5.number_input("Taxa Decimal (Ex: 0.1019)", format="%.4f")
            
            if st.form_submit_button("Gravar no Sistema"):
                if nome_cli and ns_maquina:
                    conn.table("taxas_clientes").insert({
                        "cliente": nome_cli.upper(), "ns": ns_maquina,
                        "bandeira": band, "meio": meio.lower(), "taxa_decimal": valor_taxa
                    }).execute()
                    st.success(f"Taxa salva para {nome_cli}!")
                else: st.warning("Preencha todos os campos.")

    # --- 5. ABAS: HOME / VENDAS ---
    else:
        st_autorefresh(interval=30000, key="refresh")
        try:
            df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            
            if not df_v.empty:
                # Limpeza
                df_v = df_v[df_v['lojista'].notna() & (df_v['lojista'].astype(str).str.lower() != 'nan')].copy()
                df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
                df_v = df_v.dropna(subset=['data_dt'])

                if st.session_state.perfil == "admin":
                    st.title("👨‍✈️ Painel Geral MJ")
                    lista_lj = sorted(df_v['lojista'].unique())
                    escolha = st.sidebar.multiselect("Filtrar Lojistas:", options=lista_lj, default=lista_lj)
                    v_c = df_v[df_v['lojista'].isin(escolha)].copy()
                else:
                    st.title(f"🏠 Painel: {st.session_state.usuario}")
                    v_c = df_v[df_v['lojista'] == st.session_state.usuario].copy()

                # Filtro Data
                st.sidebar.divider()
                d_ini = st.sidebar.date_input("Início", v_c['data_dt'].min().date() if not v_c.empty else datetime.now().date())
                d_fim = st.sidebar.date_input("Fim", v_c['data_dt'].max().date() if not v_c.empty else datetime.now().date())
                v_c = v_c[(v_c['data_dt'].dt.date >= d_ini) & (v_c['data_dt'].dt.date <= d_fim)]

                # Métricas
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}")
                m2.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
                m3.metric("Qtd Vendas", len(v_c))
                if st.session_state.perfil == "admin":
                    m4.metric("Seu Lucro (R$)", f"R$ {v_c['spread_rs'].sum():,.2f}")

                st.divider()
                st.dataframe(v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)

            else: st.info("Aguardando novas vendas...")
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções Comercial")
