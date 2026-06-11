import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

# Configuração de Página
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
    u, p = st.text_input("E-mail").lower().strip(), st.text_input("Senha", type="password")
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

    # --- 🏠 DASHBOARD (v113.0 - RESGATE TOTAL) ---
    if menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # 1. Puxa dados brutos
            v_res = conn.table("vendas").select("*").execute().data
            m_res = conn.table("maquinas_ns").select("*").execute().data
            p_res = conn.table("planos_mj").select("id, nome_plano").execute().data
            t_res = conn.table("taxas_dos_planos").select("*").execute().data

            if v_res:
                df_v = pd.DataFrame(v_res)
                # CORREÇÃO: Não usamos mais drop_duplicates por NS para não apagar vendas da Infinite
                df_v = df_v.drop_duplicates(subset=['id'], keep='first') # Só apaga se o ID do banco for igual

                df_m = pd.DataFrame(m_res) if m_res else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
                df_p = pd.DataFrame(p_res).rename(columns={'id': 'id_p'}); df_t = pd.DataFrame(t_res)
                
                # Normalização
                df_v['link_key'] = df_v.apply(lambda x: str(x.get('terminal', '')).strip().lstrip('0') if str(x.get('adquirente','')).lower() == 'picpay' else str(x.get('ns','')).strip().upper()[:13], axis=1)
                df_m['ns_short'] = df_m['ns'].astype(str).str.strip().str.lstrip('0').str.upper().str[:13]
                
                # Cruzamento (LEFT JOIN para não sumir nada!)
                df = pd.merge(df_v, df_m, left_on='link_key', right_on='ns_short', how='left')
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                
                df['plano_adj'] = df['plano'].astype(str).str.strip().str.lower().replace('crédito', 'à vista')
                df_t_clean = df_t.drop_duplicates(subset=['id_plano', 'bandeira', 'meio'], keep='last').rename(columns={'bandeira': 'band_p', 'meio': 'meio_p'})
                df = pd.merge(df, df_t_clean, left_on=['id_p', 'bandeira', 'plano_adj'], right_on=['id_plano', 'band_p', 'meio_p'], how='left')
                
                df['data_dt'] = df['data_venda'].apply(converter_data_seguro); df = df.dropna(subset=['data_dt'])
                df['lojista_final'] = df.apply(lambda x: x['nome_lojista'] if pd.notnull(x['nome_lojista']) else f"⚠️ NÃO VINCULADO ({x['link_key']})", axis=1)

                # Filtros
                st.sidebar.subheader("Filtros")
                lista_lj = sorted(df['lojista_final'].unique())
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", lista_lj, default=lista_lj)
                    df = df[df['lojista_final'].isin(esc)]
                else: df = df[df['lojista_final'] == st.session_state.usuario]

                # Filtro de Data
                d_ini = st.sidebar.date_input("Início", date(2026, 6, 10))
                d_fim = st.sidebar.date_input("Fim", date(2026, 6, 10))
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    # Cálculos
                    df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0).round(2)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0.0)
                    df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                    
                    st.title("📊 Dashboard Real MJ")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                    c2.metric("Líquido Total", f"R$ {df['liq'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    
                    st.divider()
                    st.dataframe(df[['data_venda', 'lojista_final', 'bandeira', 'plano', 'bruto_v', 'liq']].sort_index(ascending=False), use_container_width=True)
                else: st.warning("Sem dados no filtro.")
            else: st.info("Sincronizando...")
        except Exception as e: st.error(f"Aguardando dados... ({e})")

    # (Omitidas as outras abas Gestão/Planos/Vincular pois são as mesmas estáveis da v91.0)
    elif menu == "🏫 Gestão":
        res_e = conn.table("estabelecimentos").select("*").execute()
        if res_e.data: st.data_editor(pd.DataFrame(res_e.data), use_container_width=True, hide_index=True)
    elif menu == "📂 Planos":
        res_p = conn.table("planos_mj").select("*").execute()
        if res_p.data:
            ps = st.selectbox("Plano:", [p['nome_plano'] for p in res_p.data])
            id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
            res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
            if res_t.data:
                df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
    elif menu == "👤 Vincular":
        res_e, res_p = conn.table("estabelecimentos").select("nome_fantasia").execute(), conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vin"):
            c, ns, pl = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data]), st.text_input("NS"), st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular"):
                for n in [x.strip().upper().lstrip('0') for x in ns.split(",")]: conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                st.success("OK!")

st.sidebar.caption("MJ Soluções v113.0")
