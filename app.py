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

# Listas de ordenação fixa
ORDEM_MODALIDADES = ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard"]

def converter_data_seguro(data_str):
    try:
        if not data_str or str(data_str).lower() == 'nan': return None
        d = str(data_str).split(' •')[0].replace(',', '').strip()
        if "/" in d: return pd.to_datetime(d, dayfirst=True, errors='coerce')
        meses = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06','Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}
        for pt, num in meses.items():
            if pt in d: d = d.replace(pt, num); break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except: return None

def gerar_pdf(df, total_bruto, total_liquido):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 15, "Relatorio de Vendas - MJ Solucoes", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("helvetica", "", 12)
    pdf.cell(95, 10, f"Bruto Total: R$ {total_bruto:,.2f}", 1, align="C")
    pdf.cell(95, 10, f"Liquido a Receber: R$ {total_liquido:,.2f}", 1, ln=True, align="C")
    pdf.set_font("helvetica", "", 8)
    for _, r in df.iterrows():
        d = str(r.get('data_venda', ''))[:10]
        l = str(r.get('lojista_final', ''))[:25].encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(35, 8, d, 1); pdf.cell(60, 8, l, 1); pdf.cell(30, 8, str(r.get('bandeira', '')), 1); pdf.cell(30, 8, f"{float(r.get('bruto_v', 0)):,.2f}", 1); pdf.cell(35, 8, f"{float(r.get('liq', 0)):,.2f}", 1, ln=True)
    return bytes(pdf.output())

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u, p = st.text_input("E-mail").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if (u == "admin" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Erro!")
else:
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # (Abas Gestão e Planos mantidas v83.0)
    if menu == "🏫 Gestão":
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

    # --- 🏠 DASHBOARD (v98.0 - MODO RESGATE ATIVO) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            v_raw = conn.table("vendas").select("*").execute().data
            m_raw = conn.table("maquinas_ns").select("*").execute().data
            p_raw = conn.table("planos_mj").select("id, nome_plano").execute().data
            t_raw = conn.table("taxas_dos_planos").select("*").execute().data

            if v_raw:
                df_v = pd.DataFrame(v_raw).drop_duplicates(subset=['id'], keep='first')
                df_m = pd.DataFrame(m_raw); df_p = pd.DataFrame(p_raw).rename(columns={'id': 'id_p'}); df_t = pd.DataFrame(t_raw)
                
                df_v['link_key'] = df_v.apply(lambda x: str(x.get('terminal', '')).strip().lstrip('0') if str(x.get('adquirente','')).lower() == 'picpay' else str(x.get('ns','')).strip().upper()[:13], axis=1)
                df_m['ns_short'] = df_m['ns'].astype(str).str.strip().str.lstrip('0').str.upper().str[:13]
                
                # MUDANÇA PARA LEFT JOIN: As vendas de 16:03 vão aparecer agora como NÃO VINCULADO
                df = pd.merge(df_v, df_m, left_on='link_key', right_on='ns_short', how='left')
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                
                df['plano_adj'] = df['plano'].astype(str).str.strip().str.lower().replace('crédito', 'à vista')
                df_t_clean = df_t.drop_duplicates(subset=['id_plano', 'bandeira', 'meio'], keep='last').rename(columns={'bandeira': 'band_p', 'meio': 'meio_p'})
                df = pd.merge(df, df_t_clean, left_on=['id_p', 'bandeira', 'plano_adj'], right_on=['id_plano', 'band_p', 'meio_p'], how='left')
                
                df['data_dt'] = df['data_venda'].apply(converter_data_seguro); df = df.dropna(subset=['data_dt'])
                df['lojista_final'] = df.apply(lambda x: x['nome_lojista'] if pd.notnull(x['nome_lojista']) else f"⚠️ NÃO VINCULADO ({x['link_key']})", axis=1)

                st.sidebar.subheader("Filtros")
                l_filt = sorted(df['lojista_final'].unique())
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", l_filt, default=l_filt); df = df[df['lojista_final'].isin(esc)]
                else: df = df[df['lojista_final'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(2026, 4, 1)); d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0).round(2)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0.0)
                    df['t_cus'] = pd.to_numeric(df.get('custo_decimal', 0.0), errors='coerce').fillna(0.0)
                    df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                    df['lucro_real'] = (df['bruto_v'] * (df['t_cli'] - df['t_cus'])).round(2)
                    df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                    st.title("📊 Dashboard")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                    c2.metric("Líquido Total", f"R$ {df['liq'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    if st.session_state.perfil == "admin": c4.metric("Lucro Real", f"R$ {df['lucro_real'].sum():,.2f}")
                    st.write("---")
                    st.dataframe(df[['data_venda', 'lojista_final', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq']].sort_index(ascending=False), use_container_width=True)
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções v98.0")
