import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# --- FUNÇÕES ---
def limpar_ns(val):
    return str(val).strip().upper().lstrip('0') if val else ""

def converter_data_seguro(data_str):
    try:
        return pd.to_datetime(data_str, dayfirst=True, errors='coerce')
    except: return None

def gerar_pdf_cliente(df, total_bruto, total_liquido):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 15, "Relatorio de Vendas - MJ Solucoes", ln=True, align="C")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(95, 10, f"Bruto: R$ {total_bruto:,.2f}", 1, align="C")
    pdf.cell(95, 10, f"Liquido: R$ {total_liquido:,.2f}", 1, ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(30, 8, "Data", 1); pdf.cell(50, 8, "Cliente", 1); pdf.cell(30, 8, "Bruto", 1); pdf.cell(30, 8, "Taxa", 1); pdf.cell(50, 8, "Liquido", 1, ln=True)
    pdf.set_font("helvetica", "", 8)
    for _, r in df.iterrows():
        pdf.cell(30, 8, str(r['data_venda'])[:10], 1)
        pdf.cell(50, 8, str(r['nome_lojista']), 1)
        pdf.cell(30, 8, f"{float(r['bruto_v']):,.2f}", 1)
        pdf.cell(30, 8, str(r['taxa_txt']), 1)
        pdf.cell(50, 8, f"{float(r['liq']):,.2f}", 1, ln=True)
    return bytes(pdf.output())

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMIN"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("Erro")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABA GESTÃO ---
    if menu == "🏫 Gestão":
        st.subheader("🏫 Gestão de Clientes")
        res = conn.table("estabelecimentos").select("*").execute()
        st.data_editor(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- ABA PLANOS ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        res_p = conn.table("planos_mj").select("*").execute()
        if res_p.data:
            ps = st.selectbox("Escolha o Plano:", [p['nome_plano'] for p in res_p.data])
            id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
            res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
            if res_t.data:
                st.dataframe(pd.DataFrame(res_t.data), use_container_width=True)

    # --- ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.subheader("👤 Vincular Máquina")
        res_e, res_p = conn.table("estabelecimentos").select("nome_fantasia").execute(), conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vin"):
            c, ns, pl = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data]), st.text_input("NS"), st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular"):
                for n in [limpar(x) for x in ns.split(",") if x.strip() != ""]:
                    conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute()
                st.success("OK")

    # --- 🏠 DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="refresh")
        st.title("📊 Dashboard")
        
        # Filtros Sidebar
        d_sel = st.sidebar.date_input("Filtrar Data", date(2026, 7, 11))
        
        # Coleta de Dados
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data and m_res.data:
            df_v, df_m = pd.DataFrame(v_res.data), pd.DataFrame(m_res.data)
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id': 'id_p'})

            # Filtro Data e Link NS
            df_v['dt_obj'] = df_v['data_venda'].apply(converter_data_seguro)
            df_v = df_v[df_v['dt_obj'].dt.date == d_sel]
            df_v['link'] = df_v['ns'].apply(limpar_ns)
            df_m['link'] = df_m['ns'].apply(limpar_ns)
            
            # Cruzamento Lojista
            df = pd.merge(df_v, df_m, on='link', how='inner')
            
            if not df.empty:
                # Cruzamento Taxas
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df['pl_adj'] = df['plano'].astype(str).str.lower().replace('crédito', 'à vista')
                df_t_c = df_t.drop_duplicates(subset=['id_plano', 'bandeira', 'meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')

                # Cálculos
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                df['t_cus'] = pd.to_numeric(df.get('custo_decimal', 0), errors='coerce').fillna(0)
                df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                df['lucro_v'] = (df['bruto_v'] * (df['t_cli'] - df['t_cus'])).round(2)
                df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                if st.session_state.perfil != "admin":
                    df = df[df['nome_lojista'] == st.session_state.usuario]

                # KPIs
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                c2.metric("Líquido Total", f"R$ {df['liq'].sum():,.2f}")
                c3.metric("Vendas", len(df))
                if st.session_state.perfil == "admin":
                    c4.metric("Seu Lucro Real", f"R$ {df['lucro_v'].sum():,.2f}")

                st.divider()
                if st.button("📄 Gerar Relatório PDF"):
                    pdf = gerar_pdf_cliente(df, df['bruto_v'].sum(), df['liq'].sum())
                    st.download_button("📥 Baixar PDF", pdf, f"extrato_{d_sel}.pdf")

                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq']].sort_index(ascending=False), use_container_width=True)
            else:
                st.info("Nenhuma venda vinculada encontrada para este dia.")

st.sidebar.caption("MJ Soluções v144.0")
