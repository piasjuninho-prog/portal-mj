import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

def limpar_ns(val):
    return str(val).strip().upper().lstrip('0') if val else ""

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "mj123": st.session_state.perfil = "admin"; st.rerun()
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABA VINCULAR ---
    if menu == "👤 Vincular":
        st.subheader("👤 Vincular Nova Máquina")
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vin"):
            c = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data])
            ns = st.text_area("Digite o NS (Se for PicPay Pix, use: PICPAY_PIX)")
            pl = st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular"):
                for n in ns.split(","):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar_ns(n), "nome_lojista": c, "nome_plano": pl}).execute()
                st.success("Vinculado com Sucesso!")

    # --- ABA DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="refresh")
        st.title("📊 Dashboard")
        d_sel = st.sidebar.date_input("Data do Filtro", date(2026, 7, 20))

        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})

            # Filtro Data e Limpeza de NS
            df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt'].dt.date == d_sel]
            df_v['link'] = df_v['ns'].apply(limpar_ns)
            df_m['link'] = df_m['ns'].apply(limpar_ns)

            # --- DIAGNÓSTICO: Quais vendas estão no banco mas sem lojista vinculado? ---
            ns_no_banco = set(df_v['link'].unique())
            ns_vinculados = set(df_m['link'].unique())
            faltando = ns_no_banco - ns_vinculados
            if faltando and "" not in faltando:
                st.warning(f"⚠️ Existem vendas para os seguintes NS que não estão vinculados: **{', '.join(faltando)}**")
                st.info("Copie estes números e adicione na aba Vincular.")

            # Cruzamento (Left Join para não sumir com nada)
            df = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='left')
            df['nome_lojista'] = df['nome_lojista'].fillna("⚠️ NÃO VINCULADO")

            if not df.empty:
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                # Flexibilidade para o plano (aceita com ou sem 'x')
                df['pl_adj'] = df['plano'].astype(str).str.lower().replace('crédito', 'à vista')
                df_t_c = df_t.drop_duplicates(subset=['id_plano', 'bandeira', 'meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')

                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                c1, c2, c3 = st.columns(3)
                c1.metric("Bruto (Total no Banco)", f"R$ {df['bruto_v'].sum():,.2f}")
                c2.metric("Líquido", f"R$ {df['liq'].sum():,.2f}")
                c3.metric("Qtd Vendas", len(df))
                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq']], use_container_width=True)

st.sidebar.caption("MJ Soluções v173.0")
