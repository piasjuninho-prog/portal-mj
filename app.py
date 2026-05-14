import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# 1. Configuração de Página
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

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
    st.title("🔐 Portal MJ PAG")
    u = st.text_input("Usuário").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if (u == "admin" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Acesso negado.")
else:
    # --- MENU LATERAL COMPLETO ---
    if st.session_state.perfil == "admin":
        opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    else:
        opcoes = ["🏠 Dashboard", "🚪 Sair"]
    
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    st.sidebar.markdown(f"""<div style="background:#f0f2f6;padding:10px;border-radius:5px;border-left:5px solid #2ecc71;"><small>🔄 <b>Sincronizado:</b> {datetime.now().strftime('%H:%M:%S')}</small></div>""", unsafe_allow_html=True)
    
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 🏫 ABA GESTÃO ---
    if menu == "🏫 Gestão":
        st.title("🏫 Gestão de Clientes")
        t1, t2 = st.tabs(["📋 Lista de Clientes", "➕ Novo Cadastro"])
        with t2:
            with st.form("cad_novo"):
                n = st.text_input("Nome Fantasia"); e = st.text_input("E-mail de Login"); d = st.text_input("CNPJ/CPF"); a = st.selectbox("Adquirente", ["InfinitePay", "PicPay"])
                if st.form_submit_button("Salvar"):
                    conn.table("estabelecimentos").upsert({"nome_fantasia": n.upper().strip(), "email": e.lower().strip(), "cnpj_cpf": d, "adquirente": a, "senha": "12345"}, on_conflict="nome_fantasia").execute()
                    st.success("✅ Cadastrado!"); st.rerun()
        with t1:
            res = conn.table("estabelecimentos").select("*").execute()
            if res.data: st.data_editor(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- 📂 ABA PLANOS ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        tv, tn = st.tabs(["📋 Meus Planos", "➕ Criar Novo"])
        with tv:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                ps = st.selectbox("Plano:", [p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
        with tn:
            np = st.text_input("Nome do Plano"); bs = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
            df_ed = st.data_editor(pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo (%)": [0.0]*13}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira"):
                res = conn.table("planos_mj").upsert({"nome_plano": np.upper().strip()}, on_conflict="nome_plano").execute()
                id_p = res.data[0]['id']
                batch = [{"id_plano": id_p, "bandeira": bs, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo (%)']/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Salvo!")

    # --- 👤 ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina")
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        if res_e.data and res_p.data:
            with st.form("vinculo"):
                c = st.selectbox("Cliente", sorted([e['nome_fantasia'] for e in res_e.data]))
                ns = st.text_input("Código da Máquina (NS ou Terminal)")
                pl = st.selectbox("Plano", sorted([p['nome_plano'] for p in res_p.data]))
                if st.form_submit_button("✅ Finalizar Vínculo"):
                    conn.table("maquinas_ns").upsert({"ns": ns.strip().upper(), "nome_lojista": c, "nome_plano": pl}).execute()
                    st.success("✅ Vínculo realizado!")

    # --- 🏠 DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            v_raw = conn.table("vendas").select("*").execute().data
            m_raw = conn.table("maquinas_ns").select("*").execute().data
            p_raw = conn.table("planos_mj").select("id, nome_plano").execute().data
            t_raw = conn.table("taxas_dos_planos").select("*").execute().data

            if v_raw:
                df_v = pd.DataFrame(v_raw)
                df_m = pd.DataFrame(m_raw) if m_raw else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
                
                # Vínculo Curto para bater InfinitePay
                df_v['link_key'] = df_v.apply(lambda x: str(x.get('terminal', '')).strip().upper() if str(x.get('adquirente','')).lower() == 'picpay' else str(x.get('ns','')).strip().upper(), axis=1)
                df_v['link_key_short'] = df_v['link_key'].str[:13]
                df_m['ns_short'] = df_m['ns'].astype(str).str.strip().str.upper().str[:13]

                # Merge Vendas + Maquinas
                df = pd.merge(df_v, df_m, left_on='link_key_short', right_on='ns_short', how='left')
                df['lojista_final'] = df['nome_lojista'].fillna(df['lojista']).astype(str)

                # Merge Taxas
                df_p = pd.DataFrame(p_raw).rename(columns={'id': 'id_p'})
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df_t = pd.DataFrame(t_raw)
                for c in ['bandeira', 'meio']: df_t[c] = df_t[c].astype(str).str.strip().str.lower()
                for c in ['bandeira', 'plano']: df[c] = df[c].astype(str).str.strip().str.lower()
                df = pd.merge(df, df_t, left_on=['id_p', 'bandeira', 'plano'], right_on=['id_plano', 'bandeira', 'meio'], how='left')
                
                df['data_dt'] = df['data_venda'].apply(converter_data_seguro)
                df = df.dropna(subset=['data_dt'])
                df['data_only'] = df['data_dt'].dt.date

                # FILTRO DE LOJISTAS LIMPO (Admin vê apenas quem tem venda)
                lista_lj = sorted([x for x in df['lojista_final'].unique() if "NÃO VINCULADO" not in x])
                
                st.sidebar.subheader("Filtros")
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", sorted(df['lojista_final'].unique()), default=lista_lj)
                    df = df[df['lojista_final'].isin(esc)]
                else:
                    df = df[df['lojista_final'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(2026, 4, 1))
                d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_only'] >= d_ini) & (df['data_only'] <= d_fim)]

                if not df.empty:
                    df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                    df['liq'] = df['bruto'] * (1 - df['t_cli'])
                    
                    st.title("📊 Dashboard")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}")
                    c2.metric("Líquido Total", f"R$ {df['liq'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    st.dataframe(df[['data_venda', 'lojista_final', 'bandeira', 'plano', 'bruto', 'liq']].sort_index(ascending=False), use_container_width=True)
            else: st.info("Sem vendas.")
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções v77.0")
