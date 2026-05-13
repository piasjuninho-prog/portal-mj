import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

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
    u = st.text_input("E-mail").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Acesso negado.")
else:
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABA: DASHBOARD ---
    if menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # 1. Puxa Lista Oficial
            res_of = conn.table("estabelecimentos").select("nome_fantasia").execute()
            lista_oficial = [str(e['nome_fantasia']).upper().strip() for e in res_of.data]

            # 2. Puxa Vendas
            df = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            
            if not df.empty:
                df['lojista_up'] = df['lojista'].fillna('vazio').str.upper().str.strip()
                
                # SÓ MOSTRA SE ESTIVER NA LISTA CADASTRADA
                df = df[df['lojista_up'].isin(lista_oficial)].copy()
                
                if not df.empty:
                    df['data_dt'] = df['data_venda'].apply(converter_data)
                    df = df.dropna(subset=['data_dt'])
                    
                    st.sidebar.divider()
                    st.sidebar.subheader("Filtros")
                    lista_filt = sorted(df['lojista'].unique())
                    
                    if st.session_state.perfil == "admin":
                        esc = st.sidebar.multiselect("Lojistas:", lista_filt, default=lista_filt)
                        df = df[df['lojista'].isin(esc)]
                    else:
                        df = df[df['lojista'] == st.session_state.usuario]

                    d_ini = st.sidebar.date_input("Início", date(datetime.now().year, datetime.now().month, 1))
                    d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                    df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                    if not df.empty:
                        df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                        df['liq_c'] = pd.to_numeric(df.get('liquido_cliente', 0), errors='coerce').fillna(0)
                        t_cli = pd.to_numeric(df['taxa_cliente'], errors='coerce').fillna(0)
                        t_cus = pd.to_numeric(df.get('custo_adquirente', 0), errors='coerce').fillna(0)
                        df['lucro_rs'] = df['bruto'] * (t_cli - t_cus)

                        st.title(f"📊 Dashboard Geral MJ")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}")
                        c2.metric("Líquido Esperado", f"R$ {df['liq_c'].sum():,.2f}")
                        c3.metric("Vendas", len(df))
                        if st.session_state.perfil == "admin": c4.metric("Lucro Real", f"R$ {df['lucro_rs'].sum():,.2f}")

                        st.divider()
                        g1, g2 = st.columns(2)
                        with g1: st.line_chart(df.groupby(df['data_dt'].dt.date)['bruto'].sum())
                        with g2: st.bar_chart(df.groupby('bandeira')['bruto'].sum())

                        st.dataframe(df[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
                    else: st.warning("Sem vendas no período.")
                else: st.info("Nenhuma venda vinculada a estabelecimentos cadastrados.")
            else: st.info("Sem dados.")
        except Exception as e: st.error(f"Erro: {e}")

    # (Mantenha as abas de Gestão, Planos e Vincular como na v41.0)
    elif menu == "🏫 Gestão":
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.data_editor(pd.DataFrame(res.data), use_container_width=True)

    elif menu == "📂 Planos":
        res_p = conn.table("planos_mj").select("*").execute()
        if res_p.data:
            p_s = st.selectbox("Plano:", [p['nome_plano'] for p in res_p.data])
            id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_s)
            res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
            if res_t.data:
                df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
