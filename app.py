import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

ORDEM_MODALIDADES = ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard"]

# --- FUNÇÕES DE LIMPEZA ---
def limpar_ns(val):
    if val is None or pd.isna(val): return ""
    # Remove espaços, zeros à esquerda e converte para string pura
    return str(val).strip().upper().lstrip('0')

def converter_data_seguro(data_str):
    try:
        if not data_str: return None
        return pd.to_datetime(data_str, errors='coerce')
    except: return None

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u = st.text_input("Usuário").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Login inválido.")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # ABAS GESTÃO, PLANOS E VINCULAR (MANTIDAS)
    if menu == "🏫 Gestão":
        st.subheader("🏫 Gestão de Clientes")
        res = conn.table("estabelecimentos").select("*").execute()
        st.data_editor(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        res_p = conn.table("planos_mj").select("*").execute()
        if res_p.data:
            ps = st.selectbox("Escolha o Plano:", [p['nome_plano'] for p in res_p.data])
            id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
            res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
            if res_t.data:
                df_t_exibir = pd.DataFrame(res_t.data)
                df_piv = pd.pivot_table(df_t_exibir, values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)

    elif menu == "👤 Vincular":
        st.subheader("👤 Vincular Máquina")
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vin"):
            c = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data])
            ns = st.text_input("NS")
            pl = st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular"):
                for n in [x.strip().upper() for x in ns.split(",")]:
                    conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute()
                st.success("Vinculado!")

    # --- 🏠 DASHBOARD (MELHORADO) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="dash_ref")
        st.title("📊 Dashboard")
        
        # 1. Busca Dados Brutos
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()

        if v_res.data and m_res.data:
            df_v = pd.DataFrame(v_res.data).drop_duplicates(subset=['id'])
            df_m = pd.DataFrame(m_res.data)
            df_p = pd.DataFrame(p_res.data).rename(columns={'id': 'id_p'})
            df_t = pd.DataFrame(t_res.data)

            # 2. LIMPEZA PROFUNDA DOS NS PARA O LINK FUNCIONAR
            # PagBank e PicPay costumam salvar o NS na coluna 'terminal' ou 'ns'
            df_v['ns_link'] = df_v.apply(lambda x: limpar_ns(x.get('terminal')) if limpar_ns(x.get('terminal')) != "" else limpar_ns(x.get('ns')), axis=1)
            df_m['ns_link'] = df_m['ns'].apply(limpar_ns)

            # 3. MERGE (Cruzamento de Vendas com Lojistas)
            df = pd.merge(df_v, df_m, on='ns_link', how='inner')
            df = pd.merge(df, df_p, on='nome_plano', how='left')

            if not df.empty:
                # Join de Taxas
                df['pl_adj'] = df['plano'].astype(str).str.strip().str.lower().replace('crédito', 'à vista')
                df_t_c = df_t.drop_duplicates(subset=['id_plano', 'bandeira', 'meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                
                df['data_dt'] = df['data_venda'].apply(converter_data_seguro)
                df = df.dropna(subset=['data_dt'])

                # 4. FILTROS NA SIDEBAR
                st.sidebar.subheader("Filtros")
                opcoes_lojistas = sorted(df['nome_lojista'].unique())
                
                if st.session_state.perfil == "admin":
                    # Define todos como padrão para não começar vazio com erro
                    esc_lojistas = st.sidebar.multiselect("Lojistas:", opcoes_lojistas, default=opcoes_lojistas)
                    df = df[df['nome_lojista'].isin(esc_lojistas)]
                else:
                    df = df[df['nome_lojista'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(2026, 6, 1))
                d_fim = st.sidebar.date_input("Fim", date.today())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                # 5. CÁLCULOS FINAIS
                if not df.empty:
                    df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0.0)
                    df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                    df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                    # KPIs
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                    c2.metric("Líquido a Receber", f"R$ {df['liq'].sum():,.2f}")
                    c3.metric("Vendas", len(df))

                    st.divider()
                    st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq']].sort_index(ascending=False), use_container_width=True)
                else:
                    st.warning("Nenhuma venda para o período/lojista selecionado.")
            else:
                st.error("⚠️ Erro de Vínculo: As vendas existem no banco, mas os números de série (NS) não batem com o que foi cadastrado na aba 'Vincular'. Verifique se os NS estão corretos.")
        else:
            st.info("Aguardando carregamento de dados do Supabase...")

st.sidebar.caption("MJ Soluções v133.0")
