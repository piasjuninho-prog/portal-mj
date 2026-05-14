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
    u = st.text_input("Usuário ou E-mail").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if (u == "admin" and p == "mj123") or (u == "admin@mjpag.com" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Acesso negado.")
else:
    # --- MENU LATERAL ---
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 🏫 ABA GESTÃO (ATUALIZADA COM EXCLUIR) ---
    if menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        t_lista, t_novo, t_excluir = st.tabs(["📋 Lista", "➕ Novo Cadastro", "🗑️ Excluir Cliente"])
        
        with t_novo:
            st.subheader("Cadastrar Novo Lojista")
            with st.form("form_cad_mj", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n = c1.text_input("Nome Fantasia")
                e = c2.text_input("E-mail de Login")
                d = c1.text_input("CNPJ ou CPF")
                a = c2.selectbox("Adquirente", ["InfinitePay", "PicPay", "Stone", "Stone", "PagSeguro"])
                if st.form_submit_button("💾 Salvar Estabelecimento"):
                    if n and e:
                        conn.table("estabelecimentos").upsert({"nome_fantasia": n.upper().strip(), "email": e.lower().strip(), "cnpj_cpf": d, "adquirente": a, "senha": "12345"}, on_conflict="nome_fantasia").execute()
                        st.success("✅ Cadastrado!"); st.rerun()
                    else: st.error("Nome e E-mail são obrigatórios.")

        with t_lista:
            res_e = conn.table("estabelecimentos").select("*").execute()
            if res_e.data:
                df_e = pd.DataFrame(res_e.data)
                df_ed = st.data_editor(df_e, column_order=("nome_fantasia", "email", "senha", "adquirente", "nome_plano_ativo"), use_container_width=True, hide_index=True)
                if st.button("💾 Salvar Alterações na Lista"):
                    for _, r in df_ed.iterrows():
                        conn.table("estabelecimentos").update({"nome_fantasia": str(r["nome_fantasia"]).upper(), "email": str(r["email"]).lower(), "senha": str(r["senha"]), "adquirente": r["adquirente"]}).eq("id", r["id"]).execute()
                    st.success("✅ Atualizado!"); st.rerun()

        with t_excluir:
            st.subheader("Remover Cliente do Sistema")
            res_ex = conn.table("estabelecimentos").select("nome_fantasia").execute()
            if res_ex.data:
                lista_nomes = sorted([c['nome_fantasia'] for c in res_ex.data])
                cliente_alvo = st.selectbox("Selecione o cliente para EXCLUIR:", options=lista_nomes)
                
                st.warning(f"⚠️ Atenção: Ao excluir '{cliente_alvo}', todos os dados cadastrais dele sumirão.")
                if st.button("🚨 CONFIRMAR EXCLUSÃO PERMANENTE", use_container_width=True):
                    # 1. Remove da tabela de estabelecimentos
                    conn.table("estabelecimentos").delete().eq("nome_fantasia", cliente_alvo).execute()
                    # 2. Remove da tabela de vínculos de máquinas (NS)
                    conn.table("maquinas_ns").delete().eq("nome_lojista", cliente_alvo).execute()
                    st.success(f"O cliente {cliente_alvo} foi removido com sucesso!")
                    st.rerun()
            else:
                st.info("Nenhum cliente para excluir.")

    # --- ABAS PLANOS E VINCULAR (MANTIDAS) ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        res_p = conn.table("planos_mj").select("*").execute()
        if res_p.data:
            ps = st.selectbox("Escolha o Plano:", [p['nome_plano'] for p in res_p.data])
            id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
            res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
            if res_t.data:
                df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)

    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina")
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        if res_e.data and res_p.data:
            with st.form("v"):
                c = st.selectbox("Cliente", sorted([e['nome_fantasia'] for e in res_e.data]))
                ns = st.text_input("Código da Máquina")
                pl = st.selectbox("Plano", sorted([p['nome_plano'] for p in res_p.data]))
                if st.form_submit_button("Vincular"):
                    for n in [x.strip().upper() for x in ns.split(",")]:
                        conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                    st.success("OK!")

    # --- 🏠 DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            v_raw = conn.table("vendas").select("*").execute().data
            m_raw = conn.table("maquinas_ns").select("*").execute().data
            p_raw = conn.table("planos_mj").select("id, nome_plano").execute().data
            t_raw = conn.table("taxas_dos_planos").select("*").execute().data
            if v_raw:
                df_v = pd.DataFrame(v_raw); df_m = pd.DataFrame(m_raw) if m_raw else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
                df_v['link_key_short'] = df_v.apply(lambda x: str(x.get('terminal', '')).strip() if str(x.get('adquirente','')).lower() == 'picpay' else str(x.get('ns','')).strip()[:13], axis=1).str.upper()
                df_m['ns_short'] = df_m['ns'].astype(str).str.strip().str.upper().str[:13]
                df = pd.merge(df_v, df_m, left_on='link_key_short', right_on='ns_short', how='left')
                df['lojista_final'] = df['nome_lojista'].fillna(df['lojista']).fillna('NÃO VINCULADO').astype(str)
                df_p = pd.DataFrame(p_raw).rename(columns={'id': 'id_p'})
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df_t = pd.DataFrame(t_raw)
                for c in ['bandeira', 'meio']: df_t[c] = df_t[c].astype(str).str.strip().str.lower()
                for c in ['bandeira', 'plano']: df[c] = df[c].astype(str).str.strip().str.lower()
                df = pd.merge(df, df_t, left_on=['id_p', 'bandeira', 'plano'], right_on=['id_plano', 'bandeira', 'meio'], how='left')
                df['data_dt'] = df['data_venda'].apply(converter_data_seguro)
                df = df.dropna(subset=['data_dt'])
                df['data_only'] = df['data_dt'].dt.date
                lista_lj = sorted([str(x) for x in df['lojista_final'].unique() if x])
                st.sidebar.subheader("Filtros")
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", lista_lj, default=[x for x in lista_lj if "VINCULADO" not in x.upper()])
                    df = df[df['lojista_final'].isin(esc)]
                else: df = df[df['lojista_final'] == st.session_state.usuario]
                d_ini = st.sidebar.date_input("Início", date(2026, 4, 1)); d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_only'] >= d_ini) & (df['data_only'] <= d_fim)]
                if not df.empty:
                    df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                    df['liq'] = df['bruto'] * (1 - df['t_cli'])
                    st.title("📊 Dashboard")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}"); c2.metric("Líquido Total", f"R$ {df['liq'].sum():,.2f}"); c3.metric("Vendas", len(df))
                    st.dataframe(df[['data_venda', 'lojista_final', 'bandeira', 'plano', 'bruto', 'liq']].sort_index(ascending=False), use_container_width=True)
        except Exception as e: st.error(f"Erro no Dashboard: {e}")

st.sidebar.caption("MJ Soluções v80.0")
