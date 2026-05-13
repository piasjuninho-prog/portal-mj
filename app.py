import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

# Configuração visual
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- 1. CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Listas de ordenação fixa
ORDEM_MODALIDADES = ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard"]

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
    st.title("🔐 Portal MJ PAG PRO")
    u = st.text_input("E-mail ou Usuário").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if (u == "admin" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Acesso negado.")
else:
    # --- MENU LATERAL ---
    opcoes = ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABAS ADMIN (Omitidas aqui para brevidade, mas mantidas no código real) ---
    if menu == "🏫 Estabelecimentos":
        st.title("🏫 Gestão de Clientes")
        # (Seu código de estabelecimentos v25.1 continua aqui...)
        res_e = conn.table("estabelecimentos").select("*").execute()
        if res_e.data:
            df_e = pd.DataFrame(res_e.data)
            st.data_editor(df_e, use_container_width=True)

    elif menu == "📂 Criar Planos":
        st.title("📂 Planos de Taxas")
        nome_p = st.text_input("Nome do Plano")
        band_sel = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
        df_ed = st.data_editor(pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo Adquirente (%)": [0.0]*13}), use_container_width=True, hide_index=True)
        if st.button("💾 Salvar Bandeira"):
            res = conn.table("planos_mj").select("*").eq("nome_plano", nome_p.upper().strip()).execute()
            if not res.data: res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper().strip()}).execute()
            id_p = res.data[0]['id']
            batch = [{"id_plano": id_p, "bandeira": band_sel, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo Adquirente (%)']/100} for _, r in df_ed.iterrows()]
            conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Salvo!")

    elif menu == "👤 Vincular Cliente":
        st.title("👤 Vincular Plano")
        # (Seu código de vincular v25.1 continua aqui...)
        st.info("Selecione o cliente e o plano desejado.")

    # --- 🏠 DASHBOARD (VERSÃO AUDITORIA TOTAL) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # 1. Puxa TODAS as vendas do banco
            df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            
            if not df_v.empty:
                df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
                df_v = df_v.dropna(subset=['data_dt'])
                
                # 2. Filtros de Lojista
                lista_lj = sorted(df_v['lojista'].fillna('DESCONHECIDO').unique())
                if st.session_state.perfil == "admin":
                    escolha = st.sidebar.multiselect("Lojistas:", lista_lj, default=lista_lj)
                    df = df_v[df_v['lojista'].isin(escolha)].copy()
                else:
                    df = df_v[df_v['lojista'] == st.session_state.usuario].copy()

                # 3. Filtro de Data (Padrão: Hoje)
                d_ini = st.sidebar.date_input("Início", df['data_dt'].min().date())
                d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    # Garantir números
                    df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0)
                    df['liq_c'] = pd.to_numeric(df.get('liquido_cliente', 0.0), errors='coerce').fillna(0.0)
                    
                    # Cálculo de Lucro Real
                    t_cli = pd.to_numeric(df.get('taxa_cliente', 0.0), errors='coerce').fillna(0.0)
                    t_cus = pd.to_numeric(df.get('custo_adquirente', 0.0), errors='coerce').fillna(0.0)
                    df['lucro_rs'] = df['bruto'] * (t_cli - t_cus)

                    st.title(f"📊 Dashboard Geral MJ")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}")
                    c2.metric("Líquido Esperado", f"R$ {df['liq_c'].sum():,.2f}")
                    c3.metric("Qtd Vendas", len(df))
                    if st.session_state.perfil == "admin": 
                        c4.metric("Seu Lucro Real", f"R$ {df['lucro_rs'].sum():,.2f}")

                    st.divider()
                    # Gráficos simples para não pesar
                    g1, g2 = st.columns(2)
                    with g1: st.line_chart(df.groupby(df['data_dt'].dt.date)['bruto'].sum())
                    with g2: st.bar_chart(df.groupby('bandeira')['bruto'].sum())

                    st.subheader("📋 Detalhamento (Auditoria)")
                    # Formata taxa para aparecer como 10.19% e não 0.1019
                    exibir = df[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].copy()
                    exibir['taxa_cliente'] = (pd.to_numeric(exibir['taxa_cliente'], errors='coerce') * 100).map('{:.2f}%'.format)
                    st.dataframe(exibir.sort_index(ascending=False), use_container_width=True)
                else: st.warning("Sem vendas no filtro.")
            else: st.info("Sem dados.")
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções Comercial v42.0")
