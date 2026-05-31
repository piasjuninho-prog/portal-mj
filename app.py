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

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u = st.text_input("Usuário").lower().strip()
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
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABAS ADMIN (ESTÁVEIS) ---
    if menu == "🏫 Gestão":
        res_e = conn.table("estabelecimentos").select("*").execute()
        if res_e.data: st.data_editor(pd.DataFrame(res_e.data), use_container_width=True, hide_index=True)

    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        tv, tn = st.tabs(["📋 Meus Planos", "➕ Novo"])
        with tv:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                ps = st.selectbox("Plano:", [p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_v = pd.DataFrame(res_t.data).drop_duplicates(subset=['bandeira', 'meio'], keep='last')
                    df_piv = pd.pivot_table(df_v, values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
        with tn:
            nome_p = st.text_input("Nome do Plano"); band_s = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
            df_ed = st.data_editor(pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo (%)": [0.0]*13}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira"):
                res = conn.table("planos_mj").upsert({"nome_plano": nome_p.upper().strip()}, on_conflict="nome_plano").execute()
                id_p = res.data[0]['id']
                batch = [{"id_plano": id_p, "bandeira": band_s, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo (%)']/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Salvo!")

    elif menu == "👤 Vincular":
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        if res_e.data and res_p.data:
            with st.form("vin"):
                c = st.selectbox("Cliente", sorted([e['nome_fantasia'] for e in res_e.data])); ns = st.text_input("NS"); pl = st.selectbox("Plano", sorted([p['nome_plano'] for p in res_p.data]))
                if st.form_submit_button("Vincular"):
                    for n in [x.strip().upper().lstrip('0') for x in ns.split(",")]:
                        conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                    conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute(); st.success("Vínculo OK!")

    # --- 🏠 DASHBOARD (v95.0 - MOTOR DE DEDUPLICAÇÃO) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # 1. Busca tabelas brutas separadamente para controle total
            df_vendas = pd.DataFrame(conn.table("vendas").select("*").execute().data)
            df_maquinas = pd.DataFrame(conn.table("maquinas_ns").select("*").execute().data)
            df_taxas = pd.DataFrame(conn.table("taxas_dos_planos").select("*").execute().data)
            df_planos_ref = pd.DataFrame(conn.table("planos_mj").select("id, nome_plano").execute().data)

            if not df_vendas.empty:
                # --- DEDUPLICAÇÃO DE VENDAS (A Chave para bater o Bruto) ---
                df_vendas = df_vendas.drop_duplicates(subset=['ns'], keep='first')

                # Normalização e Casamento (Merge)
                df_vendas['link_key'] = df_vendas.apply(lambda x: str(x.get('terminal', '')).strip().lstrip('0') if str(x.get('adquirente','')).lower() == 'picpay' else str(x.get('ns','')).strip().upper()[:13], axis=1)
                df_maquinas['ns_short'] = df_maquinas['ns'].astype(str).str.strip().str.lstrip('0').str.upper().str[:13]
                
                # Unifica Vendas com Máquinas (Left Join)
                df = pd.merge(df_vendas, df_maquinas, left_on='link_key', right_on='ns_short', how='left')
                df['lojista_final'] = df.apply(lambda x: x['nome_lojista'] if pd.notnull(x['nome_lojista']) else f"⚠️ NÃO VINCULADO ({x['link_key']})", axis=1)

                # Busca Taxas
                df_p_ref = df_planos_ref.rename(columns={'id': 'id_p'})
                df = pd.merge(df, df_p_ref, on='nome_plano', how='left')
                
                df['plano_adj'] = df['plano'].astype(str).str.strip().str.lower().replace('crédito', 'à vista')
                df_t_clean = df_taxas.drop_duplicates(subset=['id_plano', 'bandeira', 'meio'], keep='last')
                df_t_clean = df_t_clean.rename(columns={'bandeira': 'band_p', 'meio': 'meio_p'})

                df = pd.merge(df, df_t_clean, left_on=['id_p', 'bandeira', 'plano_adj'], right_on=['id_plano', 'band_p', 'meio_p'], how='left')
                
                df['data_dt'] = df['data_venda'].apply(converter_data_seguro); df = df.dropna(subset=['data_dt'])

                # Filtros Sidebar
                st.sidebar.subheader("Filtros")
                lista_lj = sorted(df['lojista_final'].unique())
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", lista_lj, default=[x for x in lista_lj if "NÃO VINCULADO" not in x])
                    df = df[df['lojista_final'].isin(esc)]
                else: df = df[df['lojista_final'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(2026, 4, 1)); d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    # Cálculos finais
                    df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0).round(2)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0.0)
                    df['t_cus'] = pd.to_numeric(df['custo_decimal'], errors='coerce').fillna(0.0)
                    df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                    df['lucro_real'] = (df['bruto_v'] * (df['t_cli'] - df['t_cus'])).round(2)

                    st.title("📊 Dashboard Real")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                    c2.metric("Líquido Total", f"R$ {df['liq'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    if st.session_state.perfil == "admin": c4.metric("Lucro Real", f"R$ {df['lucro_real'].sum():,.2f}")

                    st.write("---")
                    st.dataframe(df[['data_venda', 'lojista_final', 'bandeira', 'plano', 'bruto_v', 'liq']].sort_index(ascending=False), use_container_width=True)
            else: st.info("Sem vendas sincronizadas.")
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções v95.0")
