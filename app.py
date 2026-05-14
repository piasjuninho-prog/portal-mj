import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

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

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG")
    u = st.text_input("Usuário").lower().strip()
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
    # --- MENU ---
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # (Abas de Gestão e Planos mantidas de forma estável)
    if menu == "🏫 Gestão":
        res_e = conn.table("estabelecimentos").select("*").execute()
        if res_e.data: st.data_editor(pd.DataFrame(res_e.data), use_container_width=True, hide_index=True)

    elif menu == "📂 Planos":
        res_p = conn.table("planos_mj").select("*").execute()
        if res_p.data:
            p_s = st.selectbox("Plano:", [p['nome_plano'] for p in res_p.data])
            id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_s)
            res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
            if res_t.data:
                df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)

    elif menu == "👤 Vincular":
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        if res_e.data and res_p.data:
            with st.form("vin"):
                c_s = st.selectbox("Cliente", sorted([e['nome_fantasia'] for e in res_e.data]))
                ns_i = st.text_input("NS da Maquina (ou Terminal)")
                p_s = st.selectbox("Plano", sorted([p['nome_plano'] for p in res_p.data]))
                if st.form_submit_button("Vincular"):
                    conn.table("maquinas_ns").upsert({"ns": ns_i.strip().upper(), "nome_lojista": c_s, "nome_plano": p_s}).execute()
                    st.success("Vinculo OK!")

    # --- 🏠 DASHBOARD (VERSÃO SUPER BLINDADA) ---
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
                
                # NORMALIZAÇÃO PARA O MERGE NÃO FALHAR
                df_v['link_key'] = df_v.apply(lambda x: str(x['terminal']).strip().upper() if str(x['adquirente']).lower() == 'picpay' else str(x['ns']).strip().upper(), axis=1)
                df_m['ns'] = df_m['ns'].astype(str).str.strip().upper()
                
                # Merge 1: Vendas + Maquinas (Vínculo)
                df = pd.merge(df_v, df_m, left_on='link_key', right_on='ns', how='left')
                df['lojista_final'] = df['nome_lojista'].fillna(df['lojista']).fillna('NÃO VINCULADO')

                # Merge 2: Busca ID do Plano (Normalizado)
                df_p = pd.DataFrame(p_raw).rename(columns={'id': 'id_p'})
                df_p['nome_plano'] = df_p['nome_plano'].str.strip().upper()
                df['nome_plano'] = df['nome_plano'].str.strip().upper()
                df = pd.merge(df, df_p, on='nome_plano', how='left')

                # Merge 3: Busca Taxas
                df_t = pd.DataFrame(t_raw)
                df_t['meio'] = df_t['meio'].str.strip().lower()
                df['plano'] = df['plano'].str.strip().lower()
                df['bandeira'] = df['bandeira'].str.strip().lower()
                df_t['bandeira'] = df_t['bandeira'].str.strip().lower()
                
                df = pd.merge(df, df_t, left_on=['id_p', 'bandeira', 'plano'], right_on=['id_plano', 'bandeira', 'meio'], how='left')
                
                df['data_dt'] = df['data_venda'].apply(converter_data)
                df = df.dropna(subset=['data_dt'])
                
                # Filtros
                st.sidebar.subheader("Filtros")
                l_filt = sorted(df['lojista_final'].unique())
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", l_filt, default=l_filt); df = df[df['lojista_final'].isin(esc)]
                else: df = df[df['lojista_final'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(datetime.now().year, datetime.now().month, 1))
                d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                    df['liq'] = df['bruto'] * (1 - df['t_cli'])
                    
                    st.title("📊 Dashboard Geral MJ")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}")
                    c2.metric("Líquido Esperado", f"R$ {df['liq'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    st.divider()
                    st.dataframe(df[['data_venda', 'lojista_final', 'bandeira', 'plano', 'bruto', 'liq']].sort_index(ascending=False), use_container_width=True)
            else: st.info("Sem vendas.")
        except Exception as e: st.error(f"Aguardando dados... ({e})")

st.sidebar.caption("MJ Soluções v63.0")
