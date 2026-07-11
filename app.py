import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

# 1. CONFIGURAÇÃO INICIAL (DEVE SER A PRIMEIRA COISA)
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"

try:
    conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)
except Exception as e:
    st.error(f"Erro na conexão com o banco: {e}")
    st.stop()

# --- FUNÇÕES ---
def converter_data_seguro(data_str):
    try:
        if not data_str: return None
        return pd.to_datetime(data_str, errors='coerce')
    except: return None

def gerar_pdf_cliente(df, total_bruto, total_liquido):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 15, "Relatorio de Vendas - MJ Solucoes", ln=True, align="C")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(95, 10, f"Bruto Total: R$ {total_bruto:,.2f}", 1)
    pdf.cell(95, 10, f"Liquido: R$ {total_liquido:,.2f}", 1, ln=True)
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(30, 8, "Data", 1); pdf.cell(50, 8, "Bandeira", 1); pdf.cell(30, 8, "Plano", 1); pdf.cell(30, 8, "Bruto", 1, ln=True)
    pdf.set_font("helvetica", "", 8)
    for _, r in df.iterrows():
        pdf.cell(30, 8, str(r['data_venda'])[:10], 1)
        pdf.cell(50, 8, str(r['bandeira']), 1)
        pdf.cell(30, 8, str(r['plano']), 1)
        pdf.cell(30, 8, f"R$ {float(r['bruto']):,.2f}", 1, ln=True)
    return bytes(pdf.output())

# --- SISTEMA ---
if 'perfil' not in st.session_state: st.session_state.perfil = None

if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u = st.text_input("Usuário").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Login inválido.")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Gestão", "👤 Vincular", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    if menu == "🏫 Gestão":
        st.subheader("🏫 Gestão de Clientes")
        res = conn.table("estabelecimentos").select("*").execute()
        st.data_editor(pd.DataFrame(res.data), use_container_width=True)

    elif menu == "👤 Vincular":
        st.subheader("👤 Vincular Máquina")
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vin"):
            c = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data])
            ns = st.text_input("NS (Número de Série)")
            pl = st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular"):
                for n in [x.strip().upper() for x in ns.split(",")]:
                    conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute()
                st.success("Vinculado!")

    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="auto_ref")
        st.title("📊 Dashboard")
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        
        if v_res.data and m_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data)
            
            # Normalização de NS para Link
            df_v['ns_link'] = df_v.apply(lambda x: str(x.get('terminal','')).strip() if 'PAGBANK' in str(x.get('adquirente','')).upper() else str(x.get('ns','')).strip(), axis=1)
            df_m['ns_link'] = df_m['ns'].astype(str).str.strip()
            
            df = pd.merge(df_v, df_m, left_on='ns_link', right_on='ns_link', how='inner')
            
            if st.session_state.perfil != "admin":
                df = df[df['nome_lojista'] == st.session_state.usuario]
            
            if not df.empty:
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0)
                st.metric("Faturamento Bruto", f"R$ {df['bruto_v'].sum():,.2f}")
                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v']], use_container_width=True)
                
                if st.button("📄 Gerar PDF"):
                    pdf = gerar_pdf_cliente(df, df['bruto_v'].sum(), 0)
                    st.download_button("Baixar PDF", pdf, "relatorio.pdf")
            else:
                st.info("Sem vendas vinculadas para mostrar.")

st.sidebar.caption("MJ Soluções v131.0")
