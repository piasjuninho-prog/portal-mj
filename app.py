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

def gerar_pdf(df, total_bruto, lucro):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 10, "Relatorio de Vendas - MJ Solucoes", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("helvetica", "", 12)
    pdf.cell(95, 10, f"Bruto Total: R$ {total_bruto:,.2f}", 1)
    pdf.cell(95, 10, f"Lucro Real: R$ {lucro:,.2f}", 1, ln=True)
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(35, 8, "Data", 1); pdf.cell(60, 8, "Lojista", 1); pdf.cell(30, 8, "Bandeira", 1); pdf.cell(30, 8, "Bruto", 1); pdf.cell(35, 8, "Liquido", 1, ln=True)
    pdf.set_font("helvetica", "", 8)
    for _, r in df.head(100).iterrows():
        d = str(r['data_venda']).replace('•', '-').encode('latin-1', 'replace').decode('latin-1')
        l = str(r['lojista']).encode('latin-1', 'replace').decode('latin-1')
        b = str(r['bandeira']).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(35, 8, d, 1); pdf.cell(60, 8, l[:30], 1); pdf.cell(30, 8, b, 1); pdf.cell(30, 8, f"{r['bruto']:,.2f}", 1); pdf.cell(35, 8, f"{r.get('liquido_cliente', 0):,.2f}", 1, ln=True)
    return bytes(pdf.output())

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u = st.text_input("Usuário ou E-mail").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if (u == "admin" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Credenciais inválidas.")
else:
    opcoes = ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABA: ESTABELECIMENTOS ---
    if menu == "🏫 Estabelecimentos":
        st.title("🏫 Gestão de Clientes")
        t1, t2 = st.tabs(["📋 Lista", "➕ Novo"])
        with t2:
            with st.form("cad"):
                n = st.text_input("Nome Fantasia"); e = st.text_input("E-mail"); a = st.selectbox("Adquirente", ["InfinitePay", "PicPay"])
                if st.form_submit_button("Salvar"):
                    conn.table("estabelecimentos").insert({"nome_fantasia": n.upper().strip(), "email": e.lower().strip(), "adquirente": a, "senha": "12345"}).execute()
                    st.success("OK!"); st.rerun()
        with t1:
            res = conn.table("estabelecimentos").select("*").execute()
            if res.data:
                df_ed = st.data_editor(pd.DataFrame(res.data), column_order=("nome_fantasia", "email", "senha", "adquirente", "nome_plano_ativo"), use_container_width=True, hide_index=True)
                if st.button("💾 Salvar Alterações"):
                    for _, r in df_ed.iterrows():
                        conn.table("estabelecimentos").update({"nome_fantasia": str(r["nome_fantasia"]).upper().strip(), "email": str(r["email"]).lower().strip(), "senha": str(r["senha"])}).eq("id", r["id"]).execute()
                    st.success("OK!"); st.rerun()

    elif menu == "📂 Criar Planos":
        st.title("📂 Planos de Taxas")
        t_v, t_n = st.tabs(["📋 Meus Planos", "➕ Novo"])
        with t_v:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                p_sel = st.selectbox("Escolha o Plano:", [p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_sel)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_view = pd.DataFrame(res_
