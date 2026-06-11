import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- 1. CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

ORDEM_MODALIDADES = ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard"]

def converter_data_seguro(data_str):
    try:
        if not data_str or str(data_str).lower() == 'nan': return None
        d = str(data_str).split(' •')[0].replace(',', '').strip()
        if "/" in d: return pd.to_datetime(d, dayfirst=True, errors='coerce')
        return None
    except: return None

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Acesso negado.")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # (Abas Gestão, Planos e Vincular mantidas v111.0)

    # --- 🏠 DASHBOARD v112.0 (MODO RESGATE) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # 1. Puxa tabelas brutas
            df_vendas = pd.DataFrame(conn.table("vendas").select("*").execute().data)
            df_maquinas = pd.DataFrame(conn.table("maquinas_ns").select("*").execute().data)
            df_taxas = pd.DataFrame(conn.table("taxas_dos_planos").select("*").execute().data)
            df_planos_ref = pd.DataFrame(conn.table("planos_mj").select("id, nome_plano").execute().data)

            if not df_vendas.empty:
                # Normalização de Chaves
                df_vendas['link_key'] = df_vendas.apply(lambda x: str(x.get('terminal', '')).strip().lstrip('0') if str(x.get('adquirente','')).lower() == 'picpay' else str(x.get('ns','')).strip().upper()[:13], axis=1)
                df_maquinas['ns_short'] = df_maquinas['ns'].astype(str).str.strip().str.lstrip('0').str.upper().str[:13]
                
                # MERGE LEFT: Mostra tudo, vinculado ou não
                df = pd.merge(df_vendas, df_maquinas, left_on='link_key', right_on='ns_short', how='left')
                df['lojista_final'] = df.apply(lambda x: x['nome_lojista'] if pd.notnull(x['nome_lojista']) else f"⚠️ NÃO VINCULADO (NS: {x['link_key']})", axis=1)

                # Merge Taxas
                df_p_ref = df_planos_ref.rename(columns={'id': 'id_p'})
                df = pd.merge(df, df_p_ref, on='nome_plano', how='left')
                df['pl_adj'] = df['plano'].astype(str).str.strip().str.lower().replace('crédito', 'à vista')
                df_t_clean = df_taxas.drop_duplicates(subset=['id_plano', 'bandeira', 'meio'], keep='last').rename(columns={'bandeira': 'band_p', 'meio': 'meio_p'})
                df = pd.merge(df, df_t_clean, left_on=['id_p', 'bandeira', 'pl_adj'], right_on=['id_plano', 'band_p', 'meio_p'], how='left')
                
                df['data_dt'] = df['data_venda'].apply(converter_data_seguro); df = df.dropna(subset=['data_dt'])

                # Filtros
                st.sidebar.subheader("Filtros")
                l_filt = sorted(df['lojista_final'].unique())
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", l_filt, default=l_filt)
                    df = df[df['lojista_final'].isin(esc)]
                else: df = df[df['lojista_final'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(2026, 6, 10))
                d_fim = st.sidebar.date_input("Fim", date(2026, 6, 10))
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0).round(2)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0.0)
                    df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)

                    st.title("📊 Dashboard Geral MJ")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                    c2.metric("Líquido Esperado", f"R$ {df['liq'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    
                    st.divider()
                    st.dataframe(df[['data_venda', 'lojista_final', 'bandeira', 'plano', 'bruto_v', 'liq']].sort_index(ascending=False), use_container_width=True)
            else: st.info("Sincronizando...")
        except Exception as e: st.error(f"Erro: {e}")
