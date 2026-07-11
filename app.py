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
        # Se já for objeto datetime
        if isinstance(data_str, (datetime, date)): return pd.to_datetime(data_str)
        
        d = str(data_str).split(' •')[0].replace(',', '').strip()
        # Formatos comuns: DD/MM/YYYY ou DD Mes YYYY
        if "/" in d: return pd.to_datetime(d, dayfirst=True, errors='coerce')
        
        meses = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06','Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}
        for pt, num in meses.items():
            if pt in d: d = d.replace(pt, num); break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except: return None

# --- FUNÇÃO DO PDF ---
def gerar_pdf_cliente(df, total_bruto, total_liquido):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 15, "Relatorio de Vendas - MJ Solucoes", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("helvetica", "", 12)
    pdf.cell(95, 10, f"Bruto Total: R$ {total_bruto:,.2f}", 1, align="C")
    pdf.cell(95, 10, f"Liquido a Receber: R$ {total_liquido:,.2f}", 1, ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(30, 8, "Data", 1); pdf.cell(40, 8, "Bandeira", 1); pdf.cell(30, 8, "Plano", 1); pdf.cell(30, 8, "Taxa %", 1); pdf.cell(60, 8, "Bruto", 1, ln=True)
    pdf.set_font("helvetica", "", 8)
    for _, r in df.iterrows():
        pdf.cell(30, 8, str(r['data_venda'])[:10], 1)
        pdf.cell(40, 8, str(r['bandeira']), 1)
        pdf.cell(30, 8, str(r['plano']), 1)
        pdf.cell(30, 8, str(r['taxa_txt']), 1)
        pdf.cell(60, 8, f"R$ {float(r['bruto_v']):,.2f}", 1, ln=True)
    return bytes(pdf.output())

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if (u == "admin" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            try:
                res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
                if res.data and p == str(res.data[0].get('senha', '12345')):
                    st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
                else: st.error("❌ Credenciais inválidas.")
            except: st.error("Erro de conexão com o banco de dados.")
else:
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABA GESTÃO ---
    if menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        res_e = conn.table("estabelecimentos").select("*").execute()
        if res_e.data: 
            st.data_editor(pd.DataFrame(res_e.data), use_container_width=True, hide_index=True)

    # --- ABA PLANOS ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        tv, tn = st.tabs(["📋 Meus Planos", "➕ Novo"])
        with tv:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                ps = st.selectbox("Escolha o Plano:", [p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
        with tn:
            nome_p = st.text_input("Nome do Plano"); band_s = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
            df_ed = st.data_editor(pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo (%)": [0.0]*13}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira no Plano"):
                res = conn.table("planos_mj").upsert({"nome_plano": nome_p.upper().strip()}, on_conflict="nome_plano").execute()
                id_p = res.data[0]['id']
                batch = [{"id_plano": id_p, "bandeira": band_s, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo (%)']/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Salvo!")

    # --- ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina ao Cliente")
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vin"):
            c = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data])
            ns = st.text_input("NS (Número de Série)")
            pl = st.selectbox("Plano Ativo", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular"):
                for n in [x.strip().upper().lstrip('0') for x in ns.split(",")]: 
                    conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute()
                st.success("✅ Vínculo concluído!")

    # --- 🏠 DASHBOARD (BUNKERIZADO) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="dashboard_refresh")
        try:
            # Coleta de dados com tratamento de erros
            v_res = conn.table("vendas").select("*").execute()
            m_res = conn.table("maquinas_ns").select("*").execute()
            p_res = conn.table("planos_mj").select("id, nome_plano").execute()
            t_res = conn.table("taxas_dos_planos").select("*").execute()

            if v_res.data and m_res.data:
                df_v = pd.DataFrame(v_res.data).drop_duplicates(subset=['id'])
                df_m = pd.DataFrame(m_res.data)
                df_p = pd.DataFrame(p_res.data).rename(columns={'id': 'id_p'})
                df_t = pd.DataFrame(t_res.data)

                # Chave de Link Robusta
                def gerar_key(row):
                    adq = str(row.get('adquirente','')).lower()
                    if 'picpay' in adq or 'pagbank' in adq:
                        term = str(row.get('terminal','')).strip().lstrip('0')
                        if term and term != 'None': return term[:13]
                    return str(row.get('ns','')).strip().upper().lstrip('0')[:13]

                df_v['link_key'] = df_v.apply(gerar_key, axis=1)
                df_m['ns_short'] = df_m['ns'].astype(str).str.strip().str.upper().str.lstrip('0').str[:13]
                
                # Merges
                df = pd.merge(df_v, df_m, left_on='link_key', right_on='ns_short', how='inner')
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                
                # Ajuste de Plano e Taxas
                df['pl_adj'] = df['plano'].astype(str).str.strip().str.lower().replace('crédito', 'à vista')
                df_t_c = df_t.drop_duplicates(subset=['id_plano', 'bandeira', 'meio'], keep='last').rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                
                df['data_dt'] = df['data_venda'].apply(converter_data_seguro)
                df = df.dropna(subset=['data_dt'])
                df['lojista_final'] = df['nome_lojista'].astype(str)

                # Filtros
                st.sidebar.subheader("Filtros")
                l_filt = sorted(df['lojista_final'].unique())
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", l_filt, default=l_filt)
                    df = df[df['lojista_final'].isin(esc)]
                else:
                    df = df[df['lojista_final'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(2026, 5, 30))
                d_fim = st.sidebar.date_input("Fim", date.today())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0.0)
                    df['t_cus'] = pd.to_numeric(df.get('custo_decimal', 0.0), errors='coerce').fillna(0.0)
                    
                    df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                    df['lucro_val'] = (df['bruto_v'] * (df['t_cli'] - df['t_cus'])).round(2)
                    df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                    st.title("📊 Dashboard")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                    c2.metric("Líquido Total", f"R$ {df['liq'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    if st.session_state.perfil == "admin": 
                        c4.metric("Seu Lucro Real", f"R$ {df['lucro_val'].sum():,.2f}")

                    st.divider()
                    if st.button("📄 Gerar Relatório PDF"):
                        pdf_b = gerar_pdf_cliente(df, df['bruto_v'].sum(), df['liq'].sum())
                        st.download_button("📥 Baixar PDF", pdf_b, "extrato.pdf", "application/pdf")
                    
                    st.dataframe(df[['data_venda', 'lojista_final', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq']].sort_index(ascending=False), use_container_width=True)
                else: st.info("Nenhuma venda encontrada para os filtros selecionados.")
            else: st.info("Aguardando dados de vendas e vínculos...")
        except Exception as e: 
            st.error(f"Ocorreu um erro ao processar o Dashboard. Verifique se as taxas dos planos estão cadastradas corretamente.")
            st.warning(f"Detalhe técnico: {e}")

st.sidebar.caption("MJ Soluções v129.0")
