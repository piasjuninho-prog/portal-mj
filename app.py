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
    pdf.ln(5)
    pdf.set_font("helvetica", "", 12)
    pdf.cell(95, 10, f"Bruto: R$ {total_bruto:,.2f}", 1)
    pdf.cell(95, 10, f"Lucro: R$ {lucro:,.2f}", 1, ln=True)
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(30, 8, "Data", 1); pdf.cell(50, 8, "Lojista", 1); pdf.cell(25, 8, "Bandeira", 1); pdf.cell(25, 8, "Plano", 1); pdf.cell(25, 8, "Bruto", 1); pdf.cell(35, 8, "Liquido", 1, ln=True)
    pdf.set_font("helvetica", "", 8)
    for _, r in df.head(100).iterrows():
        d = str(r.get('data_venda', '')).replace('•', '-')[:10]
        l = str(r.get('lojista', ''))[:20]
        pdf.cell(30, 8, d, 1); pdf.cell(50, 8, l, 1); pdf.cell(25, 8, str(r.get('bandeira', '')), 1); pdf.cell(25, 8, str(r.get('plano', '')), 1); pdf.cell(25, 8, f"{float(r.get('bruto', 0)):,.2f}", 1); pdf.cell(35, 8, f"{float(r.get('liquido_cliente', 0)):,.2f}", 1, ln=True)
    return bytes(pdf.output())

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
    # --- MENU LATERAL ---
    opcoes = ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 🏠 DASHBOARD ---
    if menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # 1. Carrega todas as vendas e estabelecimentos
            df_v = pd.DataFrame(conn.table("vendas").select("*").execute().data)
            df_t = pd.DataFrame(conn.table("taxas_clientes").select("*").execute().data)
            df_e = pd.DataFrame(conn.table("estabelecimentos").select("nome_fantasia").execute().data)
            
            if not df_v.empty:
                # 2. Tratamento de Nomes e Datas
                df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
                df_v = df_v.dropna(subset=['data_dt'])
                df_v['lojista'] = df_v['lojista'].fillna('NÃO IDENTIFICADO').astype(str)
                
                # 3. FILTROS NA SIDEBAR
                st.sidebar.divider(); st.sidebar.subheader("Filtros")
                
                # Lista todos os lojistas do banco (Admin vê todos)
                lista_lj = sorted(df_v['lojista'].unique())
                
                if st.session_state.perfil == "admin":
                    escolha = st.sidebar.multiselect("Lojistas:", lista_lj, default=lista_lj)
                    df = df_v[df_v['lojista'].isin(escolha)].copy()
                else:
                    df = df_v[df_v['lojista'] == st.session_state.usuario].copy()

                # Filtro de Data (Padrão: Início do mês)
                d_ini = st.sidebar.date_input("Início", date(datetime.now().year, datetime.now().month, 1))
                d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    # 4. CRUZAMENTO DE TAXAS PARA CÁLCULO REAL
                    # Casamos a venda com a tabela de taxas pelo NS + Bandeira + Plano
                    df_final = pd.merge(
                        df, df_t[['ns', 'bandeira', 'meio', 'taxa_decimal', 'custo_decimal']], 
                        left_on=['ns', 'bandeira', 'plano'], 
                        right_on=['ns', 'bandeira', 'meio'], 
                        how='left'
                    )
                    
                    # Converte para números
                    df_final['bruto'] = pd.to_numeric(df_final['bruto'], errors='coerce').fillna(0.0)
                    df_final['t_cli'] = pd.to_numeric(df_final['taxa_decimal'], errors='coerce').fillna(0.0)
                    df_final['t_cus'] = pd.to_numeric(df_final['custo_decimal'], errors='coerce').fillna(0.0)
                    
                    # Cálculos Financeiros
                    df_final['liquido_cliente'] = df_final['bruto'] * (1 - df_final['t_cli'])
                    df_final['lucro_rs'] = df_final['bruto'] * (df_final['t_cli'] - df_final['t_cus'])

                    st.title(f"📊 Dashboard Geral MJ")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Faturamento Bruto", f"R$ {df_final['bruto'].sum():,.2f}")
                    c2.metric("Líquido Esperado", f"R$ {df_final['liquido_cliente'].sum():,.2f}")
                    c3.metric("Vendas", len(df_final))
                    if st.session_state.perfil == "admin": 
                        c4.metric("Seu Lucro Real", f"R$ {df_final['lucro_rs'].sum():,.2f}")

                    st.divider()
                    g1, g2 = st.columns(2)
                    with g1: st.subheader("📈 Diário"); st.line_chart(df_final.groupby(df_final['data_dt'].dt.date)['bruto'].sum())
                    with g2: st.subheader("💳 Bandeiras"); st.bar_chart(df_final.groupby('bandeira')['bruto'].sum())
                    
                    if st.button("📄 Relatório PDF"):
                        pdf_b = gerar_pdf(df_final, df_final['bruto'].sum(), df_final['lucro_rs'].sum())
                        st.download_button("📥 Baixar PDF", pdf_b, "relatorio.pdf", "application/pdf")

                    st.write("---")
                    st.subheader("📋 Relatório de Transações")
                    st.dataframe(df_final[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
                else: st.warning("Sem vendas no período.")
            else: st.info("Aguardando sincronização.")
        except Exception as e: st.error(f"Erro: {e}")

    # --- ABA: ESTABELECIMENTOS ---
    elif menu == "🏫 Estabelecimentos":
        st.title("🏫 Gestão")
        tab1, tab2 = st.tabs(["📋 Lista", "➕ Novo"])
        with tab2:
            with st.form("cad"):
                n = st.text_input("Nome Fantasia"); e = st.text_input("E-mail"); a = st.selectbox("Adquirente", ["InfinitePay", "PicPay"])
                if st.form_submit_button("Salvar"):
                    conn.table("estabelecimentos").insert({"nome_fantasia": n.upper().strip(), "email": e.lower().strip(), "adquirente": a, "senha": "12345"}).execute()
                    st.success("OK!"); st.rerun()
        with tab1:
            res_e = conn.table("estabelecimentos").select("*").execute()
            if res_e.data:
                df_e = pd.DataFrame(res_e.data)
                df_ed = st.data_editor(df_e, column_order=("nome_fantasia", "email", "senha", "adquirente"), use_container_width=True, hide_index=True)
                if st.button("💾 Salvar Alterações"):
                    for _, r in df_ed.iterrows():
                        conn.table("estabelecimentos").update({"nome_fantasia": str(r["nome_fantasia"]).upper(), "email": str(r["email"]).lower(), "senha": str(r["senha"])}).eq("id", r["id"]).execute()
                    st.success("OK!"); st.rerun()

    # --- ABA: PLANOS ---
    elif menu == "📂 Planos":
        st.title("📂 Planos")
        tab_v, tab_n = st.tabs(["📋 Meus Planos", "➕ Novo"])
        with tab_v:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                p_s = st.selectbox("Plano:", [p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_s)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
        with tab_n:
            nome_p = st.text_input("Nome"); band_s = st.selectbox("Bandeira", ORDEM_BANDEIRAS)
            df_ed = st.data_editor(pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo Adquirente (%)": [0.0]*13}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar"):
                res = conn.table("planos_mj").select("*").eq("nome_plano", nome_p.upper()).execute()
                if not res.data: res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper()}).execute()
                id_p = res.data[0]['id']
                batch = [{"id_plano": id_p, "bandeira": band_s, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo Adquirente (%)']/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute(); st.success("OK!")

    # --- ABA: VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular")
        res_p = conn.table("planos_mj").select("id, nome_plano").execute()
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        if res_p.data and res_e.data:
            d_p = {p['nome_plano']: p['id'] for p in res_p.data}; l_c = sorted([str(e['nome_fantasia']) for e in res_e.data])
            with st.form("vin"):
                c_s = st.selectbox("Cliente", l_c); ns_i = st.text_input("NS (Vírgula)"); p_s = st.selectbox("Plano", list(d_p.keys()))
                if st.form_submit_button("Vincular"):
                    res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", d_p[p_s]).execute()
                    for ns in [n.strip() for n in ns_i.split(",")]:
                        novas = [{"cliente": c_s, "ns": ns, "bandeira": t['bandeira'], "meio": t['meio'], "taxa_decimal": t['taxa_decimal'], "custo_decimal": t.get('custo_decimal', 0.0)} for t in res_t.data]
                        conn.table("taxas_clientes").insert(novas).execute()
                    conn.table("estabelecimentos").update({"nome_plano_ativo": p_s}).eq("nome_fantasia", c_s).execute(); st.success("OK!")

st.sidebar.caption("MJ Soluções Comercial v41.0")
