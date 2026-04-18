import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
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
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatorio de Vendas - MJ Solucoes", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(95, 10, f"Bruto Total: R$ {total_bruto:,.2f}", 1)
    pdf.cell(95, 10, f"Lucro Real: R$ {lucro:,.2f}", 1, ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 8, "Data", 1); pdf.cell(60, 8, "Lojista", 1); pdf.cell(30, 8, "Bandeira", 1); pdf.cell(30, 8, "Bruto", 1); pdf.cell(40, 8, "Liquido", 1, ln=True)
    pdf.set_font("Arial", "", 9)
    for _, r in df.head(50).iterrows():
        pdf.cell(30, 8, str(r['data_venda']), 1); pdf.cell(60, 8, str(r['lojista'])[:25], 1); pdf.cell(30, 8, str(r['bandeira']), 1); pdf.cell(30, 8, f"{r['bruto']:,.2f}", 1); pdf.cell(40, 8, f"{r['liquido_cliente']:,.2f}", 1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- 2. LOGIN ---
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
            else: st.error("❌ Usuário ou senha incorretos.")
else:
    # --- 3. MENU LATERAL ---
    opcoes = ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    st.sidebar.markdown(f"""<div style="background:#f0f2f6;padding:10px;border-radius:5px;border-left:5px solid #2ecc71;"><small>🔄 <b>Sincronizado:</b> {datetime.now().strftime('%H:%M:%S')}</small></div>""", unsafe_allow_html=True)
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 4. ABA: ESTABELECIMENTOS ---
    if menu == "🏫 Estabelecimentos":
        st.title("🏫 Gestão de Estabelecimentos")
        tab_list, tab_cad = st.tabs(["📋 Lista de Clientes", "➕ Novo Cadastro"])
        with tab_cad:
            with st.form("cad_est", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nome_f = c1.text_input("Nome Fantasia")
                email_cli = c2.text_input("E-mail de Login")
                adq = st.selectbox("Adquirente", ["InfinitePay", "PicPay", "Stone"])
                if st.form_submit_button("💾 Salvar"):
                    conn.table("estabelecimentos").insert({"nome_fantasia": nome_f.upper().strip(), "email": email_cli.lower().strip(), "adquirente": adq, "senha": "12345"}).execute()
                    st.success("Cadastrado!"); st.rerun()
        with tab_list:
            res_e = conn.table("estabelecimentos").select("*").execute()
            if res_e.data:
                df_e = pd.DataFrame(res_e.data)
                df_ed = st.data_editor(df_e, column_order=("nome_fantasia", "email", "senha", "adquirente", "nome_plano_ativo"), use_container_width=True, hide_index=True)
                if st.button("💾 Salvar Alterações"):
                    for _, r in df_ed.iterrows():
                        conn.table("estabelecimentos").update({"nome_fantasia": r["nome_fantasia"].upper(), "email": r["email"].lower(), "senha": r["senha"]}).eq("id", r["id"]).execute()
                    st.success("Atualizado!"); st.rerun()

    # --- 5. ABA: CRIAR PLANOS (TAXA INTEIRA + CUSTO) ---
    elif menu == "📂 Criar Planos":
        st.title("📂 Planos de Taxas")
        tab_v, tab_n = st.tabs(["📋 Meus Planos", "➕ Criar Novo Plano"])
        with tab_v:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                p_sel = st.selectbox("Plano:", [p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_sel)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_piv = pd.DataFrame(res_t.data).pivot(index='meio', columns='bandeira', values='taxa_decimal').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
        with tab_n:
            nome_p = st.text_input("Nome do Plano")
            band_sel = st.selectbox("Configurar Bandeira:", ORDEM_BANDEIRAS)
            df_setup = pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo Adquirente (%)": [0.0]*13})
            df_ed = st.data_editor(df_setup, use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira"):
                res = conn.table("planos_mj").select("*").eq("nome_plano", nome_p.upper()).execute()
                if not res.data: res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper()}).execute()
                id_p = res.data[0]['id']
                batch = []
                for _, r in df_ed.iterrows():
                    batch.append({"id_plano": id_p, "bandeira": band_sel, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo Adquirente (%)']/100})
                conn.table("taxas_dos_planos").insert(batch).execute()
                st.success(f"{band_sel.capitalize()} salvo no plano!")

    # --- 6. ABA: VINCULAR CLIENTE ---
    elif menu == "👤 Vincular Cliente":
        st.title("👤 Vincular Plano")
        res_p = conn.table("planos_mj").select("id, nome_plano").execute()
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        if res_p.data and res_e.data:
            d_p = {p['nome_plano']: p['id'] for p in res_p.data}
            l_c = sorted([e['nome_fantasia'] for e in res_e.data])
            with st.form("vinculo"):
                c_sel = st.selectbox("Estabelecimento", l_c); ns_in = st.text_input("NS (Separe por vírgula)"); p_sel = st.selectbox("Plano", list(d_p.keys()))
                if st.form_submit_button("✅ FINALIZAR"):
                    res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", d_p[p_sel]).execute()
                    for ns in [n.strip() for n in ns_in.split(",")]:
                        novas = [{"cliente": c_sel, "ns": ns, "bandeira": t['bandeira'], "meio": t['meio'], "taxa_decimal": t['taxa_decimal'], "custo_decimal": t.get('custo_decimal', 0)} for t in res_t.data]
                        conn.table("taxas_clientes").insert(novas).execute()
                    conn.table("estabelecimentos").update({"nome_plano_ativo": p_sel}).eq("nome_fantasia", c_sel).execute()
                    st.success("Vínculo OK!")

    # --- 7. ABA: DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            df = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            if not df.empty:
                df['data_dt'] = df['data_venda'].apply(converter_data)
                df = df.dropna(subset=['data_dt'])
                
                # Filtros
                st.sidebar.subheader("Filtros")
                lista_lj = sorted(df['lojista'].unique())
                if st.session_state.perfil == "admin":
                    escolha = st.sidebar.multiselect("Lojistas:", lista_lj, default=lista_lj)
                    df = df[df['lojista'].isin(escolha)]
                else:
                    df = df[df['lojista'] == st.session_state.usuario]
                
                d_ini = st.sidebar.date_input("Início", df['data_dt'].min().date())
                d_fim = st.sidebar.date_input("Fim", df['data_dt'].max().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                # Cálculos
                bruto = df['bruto'].sum()
                liquido = df['liquido_cliente'].sum()
                # Lucro Real = Bruto * (Taxa Cliente - Taxa Custo)
                df['taxa_c'] = pd.to_numeric(df['taxa_cliente'], errors='coerce').fillna(0)
                df['custo_a'] = pd.to_numeric(df.get('custo_adquirente', 0), errors='coerce').fillna(0)
                df['lucro_rs'] = df['bruto'] * (df['taxa_c'] - df['custo_a'])
                lucro_total = df['lucro_rs'].sum()

                st.title(f"📊 Painel Geral MJ")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
                c2.metric("Líquido Esperado", f"R$ {liquido:,.2f}")
                c3.metric("Qtd Vendas", len(df))
                if st.session_state.perfil == "admin": c4.metric("Seu Lucro Real", f"R$ {lucro_total:,.2f}")

                # Gráficos
                st.divider()
                g1, g2 = st.columns(2)
                with g1: st.subheader("📈 Faturamento por Dia"); st.line_chart(df.groupby(df['data_dt'].dt.date)['bruto'].sum())
                with g2: st.subheader("💳 Vendas por Bandeira"); st.bar_chart(df.groupby('bandeira')['bruto'].sum())

                if st.button("📄 Gerar Relatório PDF"):
                    pdf_b = gerar_pdf(df, bruto, lucro_total)
                    st.download_button("📥 Baixar PDF", pdf_b, "relatorio.pdf", "application/pdf")

                st.write("---")
                st.dataframe(df[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
            else: st.info("Sem vendas sincronizadas.")
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções Comercial v17.0")
