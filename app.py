import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# 1. Configuração de Página
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONEXÃO ---
URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=URL, key=KEY)

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

# --- 3. LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u = st.text_input("Usuário").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMIN"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Acesso negado.")
else:
    # --- 4. MENU ---
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 5. DASHBOARD (LÓGICA REFEITA) ---
    if menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="f5")
        try:
            # Busca dados e garante que é um DataFrame
            vendas_data = conn.table("dashboard_vendas").select("*").execute().data
            df = pd.DataFrame(vendas_data)

            if not df.empty:
                # Tratamento de datas
                df['data_dt'] = df['data_venda'].apply(converter_data)
                df = df.dropna(subset=['data_dt'])
                
                # Tratamento de lojistas para evitar erro de float/str
                df['lojista'] = df['lojista'].astype(str).replace('nan', 'DESCONHECIDO')
                
                # Filtros Sidebar
                st.sidebar.subheader("Filtros")
                if st.session_state.perfil == "admin":
                    lista_lj = sorted(df['lojista'].unique())
                    esc = st.sidebar.multiselect("Lojistas:", lista_lj, default=lista_lj)
                    df = df[df['lojista'].isin(esc)]
                else:
                    df = df[df['lojista'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(datetime.now().year, datetime.now().month, 1))
                d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    # --- CÁLCULOS SEM FILLNA (PROTEÇÃO TOTAL) ---
                    # Garante que colunas existem
                    for c in ['bruto', 'liquido_cliente', 'taxa_cliente', 'custo_adquirente']:
                        if c not in df.columns: df[c] = 0.0
                        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

                    # Cálculo do lucro
                    df['lucro_rs'] = df['bruto'] * (df['taxa_cliente'] - df['custo_adquirente'])

                    # Métricas
                    st.title(f"📊 Dashboard Geral MJ")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}")
                    c2.metric("Líquido Total", f"R$ {df['liquido_cliente'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    if st.session_state.perfil == "admin":
                        c4.metric("Lucro Real", f"R$ {df['lucro_rs'].sum():,.2f}")

                    st.divider()
                    g1, g2 = st.columns(2)
                    with g1: st.line_chart(df.groupby(df['data_dt'].dt.date)['bruto'].sum())
                    with g2: st.bar_chart(df.groupby('bandeira')['bruto'].sum())
                    
                    st.write("---")
                    st.dataframe(df[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
                else: st.warning("Sem dados no período.")
            else: st.info("Sem vendas.")
        except Exception as e:
            st.error(f"Erro no processamento: {e}")

    # --- ABAS ADMIN (SIMPLIFICADAS PARA NÃO DAR ERRO) ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão")
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.data_editor(pd.DataFrame(res.data), use_container_width=True)

    elif menu == "📂 Planos":
        st.title("📂 Planos")
        res_p = conn.table("planos_mj").select("*").execute()
        if res_p.data:
            p_s = st.selectbox("Plano:", [p['nome_plano'] for p in res_p.data])
            id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_s)
            res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
            if res_t.data:
                df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)

    elif menu == "👤 Vincular":
        st.title("👤 Vincular")
        res_p = conn.table("planos_mj").select("id, nome_plano").execute()
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        if res_p.data and res_e.data:
            with st.form("vin"):
                c_s = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data])
                ns_i = st.text_input("NS (Separar por vírgula)")
                p_s = st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
                if st.form_submit_button("Vincular"):
                    id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_s)
                    res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                    for ns in [n.strip() for n in ns_i.split(",")]:
                        novas = [{"cliente": c_s, "ns": ns, "bandeira": t['bandeira'], "meio": t['meio'], "taxa_decimal": t['taxa_decimal'], "custo_decimal": t.get('custo_decimal', 0)} for t in res_t.data]
                        conn.table("taxas_clientes").insert(novas).execute()
                    conn.table("estabelecimentos").update({"nome_plano_ativo": p_s}).eq("nome_fantasia", c_s).execute(); st.success("Vínculo OK!")

st.sidebar.caption("MJ Soluções v48.0")
