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
    for _, r in df.head(50).iterrows():
        d = str(r.get('data_venda', '')).replace('•', '-').encode('latin-1', 'replace').decode('latin-1')
        l = str(r.get('lojista', ''))[:25].encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(35, 8, d, 1); pdf.cell(60, 8, l, 1); pdf.cell(30, 8, str(r.get('bandeira', '')), 1); pdf.cell(30, 8, f"{float(r.get('bruto', 0)):,.2f}", 1); pdf.cell(40, 8, f"{float(r.get('liquido_cliente', 0)):,.2f}", 1, ln=True)
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
    # --- MENU LATERAL ---
    opcoes = ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABA: DASHBOARD (FOCO NO CONSERTO DO ERRO) ---
    if menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # 1. Puxa vendas do banco
            raw_vendas = conn.table("dashboard_vendas").select("*").execute().data
            df = pd.DataFrame(raw_vendas)
            
            if not df.empty:
                # 2. TRATAMENTO DE TIPOS (Evita erro float vs str)
                df['lojista'] = df['lojista'].fillna('DESCONHECIDO').astype(str)
                df['data_dt'] = df['data_venda'].apply(converter_data)
                df = df.dropna(subset=['data_dt'])
                
                # 3. FILTROS NA SIDEBAR
                st.sidebar.divider()
                if st.session_state.perfil == "admin":
                    lista_lj = sorted(df['lojista'].unique())
                    escolha = st.sidebar.multiselect("Filtrar Lojistas:", lista_lj, default=lista_lj)
                    df = df[df['lojista'].isin(escolha)]
                else:
                    df = df[df['lojista'] == st.session_state.usuario]

                # Filtro de Data
                d_ini = st.sidebar.date_input("Início", df['data_dt'].min().date())
                d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    # --- CÁLCULO FINANCEIRO BLINDADO ---
                    # Transformamos colunas em Séries numéricas antes de qualquer fillna
                    bruto_col = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0)
                    liq_col = pd.to_numeric(df['liquido_cliente'], errors='coerce').fillna(0.0)
                    
                    # Garante que taxa e custo existem como colunas (Series)
                    taxa_c_col = pd.to_numeric(df['taxa_cliente'], errors='coerce').fillna(0.0) if 'taxa_cliente' in df.columns else pd.Series([0.0]*len(df))
                    custo_a_col = pd.to_numeric(df.get('custo_adquirente', 0.0), errors='coerce')
                    
                    # Se custo_a_col for apenas um número, transformamos em coluna de zeros
                    if isinstance(custo_a_col, (int, float)):
                        custo_a_col = pd.Series([0.0]*len(df))
                    else:
                        custo_a_col = custo_a_col.fillna(0.0)

                    # Calcula lucro linha a linha
                    df['lucro_calculado'] = bruto_col * (taxa_c_col - custo_a_col)

                    st.title(f"📊 Dashboard Geral MJ")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Bruto Total", f"R$ {bruto_col.sum():,.2f}")
                    c2.metric("Líquido Total", f"R$ {liq_col.sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    if st.session_state.perfil == "admin": 
                        c4.metric("Seu Lucro Real", f"R$ {df['lucro_calculado'].sum():,.2f}")

                    st.divider()
                    g1, g2 = st.columns(2)
                    with g1: st.subheader("📈 Diario"); st.line_chart(df.groupby(df['data_dt'].dt.date)['bruto'].sum())
                    with g2: st.subheader("💳 Bandeira"); st.bar_chart(df.groupby('bandeira')['bruto'].sum())
                    
                    if st.button("📄 Relatorio PDF"):
                        pdf_b = gerar_pdf(df, bruto_col.sum(), df['lucro_calculado'].sum())
                        st.download_button("📥 Baixar PDF", pdf_b, "relatorio.pdf", "application/pdf")

                    st.write("---")
                    st.dataframe(df[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
                else: st.warning("Filtro sem resultados.")
            else: st.info("Sem vendas sincronizadas.")
        except Exception as e: st.error(f"Erro no processamento: {e}")

    # Manutenção das outras abas (Estabelecimentos, Planos, Vincular)
    elif menu == "🏫 Estabelecimentos":
        st.title("🏫 Gestão")
        res_e = conn.table("estabelecimentos").select("*").execute()
        if res_e.data:
            df_e = pd.DataFrame(res_e.data)
            st.data_editor(df_e, use_container_width=True, hide_index=True)

    elif menu == "📂 Criar Planos":
        st.title("📂 Planos")
        nome_p = st.text_input("Nome do Plano"); band_sel = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
        df_ed = st.data_editor(pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo Adquirente (%)": [0.0]*13}), use_container_width=True, hide_index=True)
        if st.button("💾 Salvar"):
            res = conn.table("planos_mj").select("*").eq("nome_plano", nome_p.upper()).execute()
            if not res.data: res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper()}).execute()
            id_p = res.data[0]['id']
            batch = [{"id_plano": id_p, "bandeira": band_sel, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo Adquirente (%)']/100} for _, r in df_ed.iterrows()]
            conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Salvo!")

    elif menu == "👤 Vincular Cliente":
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
                    conn.table("estabelecimentos").update({"nome_plano_ativo": p_s}).eq("nome_fantasia", c_s).execute(); st.success("Vínculo OK!")

st.sidebar.caption("MJ Soluções Comercial v43.0")
