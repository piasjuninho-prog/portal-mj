import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
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
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatório de Vendas - MJ Soluções", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Data do Relatório: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(95, 10, f"Bruto Total: R$ {total_bruto:,.2f}", border=1)
    pdf.cell(95, 10, f"Lucro Total: R$ {lucro:,.2f}", border=1, ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Data", 1); pdf.cell(60, 8, "Lojista", 1); pdf.cell(30, 8, "Bandeira", 1); pdf.cell(30, 8, "Bruto", 1); pdf.cell(40, 8, "Líquido", 1, ln=True)
    pdf.set_font("Arial", "", 9)
    for _, r in df.head(100).iterrows():
        pdf.cell(30, 8, str(r['data_venda']), 1); pdf.cell(60, 8, str(r['lojista'])[:25], 1); pdf.cell(30, 8, str(r['bandeira']), 1); pdf.cell(30, 8, f"{r['bruto']:,.2f}", 1); pdf.cell(40, 8, f"{r['liquido_cliente']:,.2f}", 1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 MJ PAG PRO - Acesso")
    u = st.text_input("E-mail ou Usuário").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if (u == "admin" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("Erro!")
else:
    # --- MENU ---
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 📂 CRIAR PLANOS (AGORA COM CUSTO E NUMERO INTEIRO) ---
    if menu == "📂 Criar Planos" and st.session_state.perfil == "admin":
        st.title("📂 Gestão de Planos de Taxas")
        tab_v, tab_n = st.tabs(["📋 Meus Planos", "➕ Criar Novo Plano"])
        with tab_n:
            nome_p = st.text_input("Nome do Plano")
            band_sel = st.selectbox("Selecione a Bandeira para configurar:", ORDEM_BANDEIRAS)
            df_setup = pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo Adquirente (%)": [0.0]*13})
            df_ed = st.data_editor(df_setup, use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira no Plano"):
                res = conn.table("planos_mj").select("*").eq("nome_plano", nome_p.upper()).execute()
                if not res.data:
                    res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper()}).execute()
                id_p = res.data[0]['id']
                batch = []
                for _, r in df_ed.iterrows():
                    batch.append({"id_plano": id_p, "bandeira": band_sel, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo Adquirente (%)']/100})
                conn.table("taxas_dos_planos").insert(batch).execute()
                st.success(f"Taxas {band_sel} salvas!")

    # --- 🏠 DASHBOARD (COM GRÁFICOS E PDF) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            res_oficial = conn.table("estabelecimentos").select("nome_fantasia").execute()
            lista_oficial = [e['nome_fantasia'] for e in res_oficial.data]
            df = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            
            if not df.empty:
                df = df[df['lojista'].isin(lista_oficial)].copy()
                df['data_dt'] = df['data_venda'].apply(converter_data)
                if st.session_state.perfil == "admin":
                    escolha = st.sidebar.multiselect("Lojistas:", lista_oficial, default=lista_oficial)
                    df = df[df['lojista'].isin(escolha)]
                else:
                    df = df[df['lojista'] == st.session_state.usuario]

                st.title(f"📊 Dashboard: {st.session_state.usuario}")
                
                # Cálculos de Lucro Real (Bruto * (Taxa Cliente - Taxa Custo))
                df['spread_rs'] = df['bruto'] * (pd.to_numeric(df['taxa_cliente'], errors='coerce') - pd.to_numeric(df.get('custo_adquirente', 0), errors='coerce'))
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Faturamento Bruto", f"R$ {df['bruto'].sum():,.2f}")
                m2.metric("Líquido Total", f"R$ {df['liquido_cliente'].sum():,.2f}")
                m3.metric("Vendas", len(df))
                m4.metric("Seu Lucro Real", f"R$ {df['spread_rs'].sum():,.2f}")

                # --- GRÁFICOS ---
                st.divider()
                c_graf1, c_graf2 = st.columns(2)
                with c_graf1:
                    st.subheader("📈 Evolução Diária (Bruto)")
                    df_day = df.groupby(df['data_dt'].dt.date)['bruto'].sum()
                    st.line_chart(df_day)
                with c_graf2:
                    st.subheader("💳 Vendas por Bandeira")
                    df_band = df.groupby('bandeira')['bruto'].sum()
                    st.bar_chart(df_band)

                # --- PDF ---
                st.divider()
                if st.button("📄 Gerar Relatório em PDF"):
                    pdf_bytes = gerar_pdf(df, df['bruto'].sum(), df['spread_rs'].sum())
                    st.download_button("📥 Baixar PDF", pdf_bytes, file_name="relatorio_vendas.pdf", mime="application/pdf")

                st.subheader("📋 Detalhamento")
                st.dataframe(df[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
        except Exception as e: st.error(f"Erro: {e}")

    # --- ABA: ESTABELECIMENTOS E VINCULO (Mantidas) ---
    # ... (O restante do código de Estabelecimentos e Vinculo segue a mesma lógica anterior)
