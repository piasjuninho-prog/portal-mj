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
            else: st.error("❌ Acesso negado.")
else:
    # --- MENU LATERAL ---
    opcoes = ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    st.sidebar.markdown(f"""<div style="background:#f0f2f6;padding:10px;border-radius:5px;border-left:5px solid #2ecc71;"><small>🔄 <b>Sincronizado:</b> {datetime.now().strftime('%H:%M:%S')}</small></div>""", unsafe_allow_html=True)
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABA: DASHBOARD (CÁLCULO DINÂMICO VIA PLANOS) ---
    if menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # 1. Puxa as 3 tabelas necessárias
            df_vendas = pd.DataFrame(conn.table("vendas").select("*").execute().data)
            df_estab = pd.DataFrame(conn.table("estabelecimentos").select("nome_fantasia, nome_plano_ativo").execute().data)
            df_planos = pd.DataFrame(conn.table("taxas_dos_planos").select("id_plano, bandeira, meio, taxa_decimal, custo_decimal").execute().data)
            df_nomes_planos = pd.DataFrame(conn.table("planos_mj").select("id, nome_plano").execute().data)

            if not df_vendas.empty and not df_estab.empty and not df_planos.empty:
                # 2. Casamento 1: Venda + Estabelecimento (para saber o plano)
                df = pd.merge(df_vendas, df_estab, left_on='lojista', right_on='nome_fantasia', how='left')
                
                # 3. Casamento 2: Plano MJ (para pegar o ID do plano pelo nome)
                df = pd.merge(df, df_nomes_planos, left_on='nome_plano_ativo', right_on='nome_plano', how='left')

                # 4. Casamento 3: Venda + Taxas do Plano (Merge Final)
                df = pd.merge(
                    df, df_planos, 
                    left_on=['id', 'bandeira', 'plano'], 
                    right_on=['id_plano', 'bandeira', 'meio'], 
                    how='left'
                )

                # Tratamento de datas
                df['data_dt'] = df['data_venda'].apply(converter_data)
                df = df.dropna(subset=['data_dt'])
                
                # Filtros Sidebar
                st.sidebar.divider(); st.sidebar.subheader("Filtros")
                lista_lj = sorted(df['lojista'].unique())
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", lista_lj, default=lista_lj)
                    df = df[df['lojista'].isin(esc)]
                else:
                    df = df[df['lojista'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(datetime.now().year, datetime.now().month, 1))
                d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    # Cálculos Financeiros
                    df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0.0)
                    df['t_cus'] = pd.to_numeric(df.get('custo_decimal', 0.0), errors='coerce').fillna(0.0)
                    
                    df['liquido_esperado'] = df['bruto'] * (1 - df['t_cli'])
                    df['lucro_rs'] = df['bruto'] * (df['t_cli'] - df['t_cus'])

                    st.title(f"📊 Dashboard Geral MJ")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}")
                    c2.metric("Líquido Esperado", f"R$ {df['liquido_esperado'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    if st.session_state.perfil == "admin": 
                        c4.metric("Seu Lucro Real", f"R$ {df['lucro_rs'].sum():,.2f}")

                    st.divider()
                    st.subheader("📋 Relatório de Transações (Calculado via Planos)")
                    exibir = df[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_decimal', 'liquido_esperado']].copy()
                    exibir['taxa_decimal'] = (exibir['taxa_decimal'] * 100).map('{:.2f}%'.format)
                    st.dataframe(exibir.sort_index(ascending=False), use_container_width=True)
                else: st.warning("Sem vendas no período.")
            else: st.info("Certifique-se de ter cadastrado estabelecimentos e planos de taxas.")
        except Exception as e: st.error(f"Erro: {e}")

    # --- OUTRAS ABAS (MANTIDAS) ---
    elif menu == "🏫 Estabelecimentos":
        st.title("🏫 Gestão")
        res_e = conn.table("estabelecimentos").select("*").execute()
        if res_e.data:
            df_ed = st.data_editor(pd.DataFrame(res_e.data), column_order=("nome_fantasia", "email", "senha", "adquirente", "nome_plano_ativo"), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar"):
                for _, r in df_ed.iterrows():
                    conn.table("estabelecimentos").update({"nome_fantasia": str(r["nome_fantasia"]).upper(), "email": str(r["email"]).lower(), "senha": str(r["senha"])}).eq("id", r["id"]).execute()
                st.success("OK!"); st.rerun()

    elif menu == "📂 Criar Planos":
        st.title("📂 Planos")
        nome_p = st.text_input("Nome do Plano"); band_sel = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
        df_ed = st.data_editor(pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo Adquirente (%)": [0.0]*13}), use_container_width=True, hide_index=True)
        if st.button("💾 Salvar Bandeira"):
            res = conn.table("planos_mj").select("*").eq("nome_plano", nome_p.upper().strip()).execute()
            if not res.data: res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper().strip()}).execute()
            id_p = res.data[0]['id']
            batch = [{"id_plano": id_p, "bandeira": band_sel, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo Adquirente (%)']/100} for _, r in df_ed.iterrows()]
            conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Salvo!"); st.rerun()

    elif menu == "👤 Vincular Cliente":
        st.title("👤 Vincular")
        res_p = conn.table("planos_mj").select("id, nome_plano").execute()
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        if res_p.data and res_e.data:
            with st.form("vin"):
                c_s = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data])
                p_s = st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
                if st.form_submit_button("Vincular"):
                    conn.table("estabelecimentos").update({"nome_plano_ativo": p_s}).eq("nome_fantasia", c_s).execute()
                    st.success(f"Vínculo OK! {c_s} agora usa {p_s}")

st.sidebar.caption("MJ Soluções Comercial v50.0")
