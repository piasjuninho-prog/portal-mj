import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

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
    st.title("🔐 Portal MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Login inválido.")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Gestão", "👤 Vincular", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    if menu == "🏫 Gestão":
        res = conn.table("estabelecimentos").select("*").execute()
        st.data_editor(pd.DataFrame(res.data), use_container_width=True)

    elif menu == "👤 Vincular":
        st.subheader("👤 Vincular Nova Máquina")
        res_e, res_p = conn.table("estabelecimentos").select("nome_fantasia").execute(), conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vin"):
            c = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data])
            ns, pl = st.text_input("NS (Número de Série)"), st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular"):
                for n in [limpar_ns(x) for x in ns.split(",") if x.strip() != ""]:
                    conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute()
                st.success("✅ Máquina vinculada!")

    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="refresh")
        st.title("📊 Dashboard")
        
        # Filtros
        st.sidebar.subheader("Filtros")
        d_sel = st.sidebar.date_input("Data", date(2026, 7, 11))

        # Dados
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data and m_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data)
            df_t = pd.DataFrame(t_res.data)
            df_p = pd.DataFrame(p_res.data).rename(columns={'id': 'id_p'})

            # Filtro por data
            df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt'].dt.date == d_sel]

            # Cruzamento
            df_v['ns_link'] = df_v['ns'].apply(limpar_ns)
            df_m['ns_link'] = df_m['ns'].apply(limpar_ns)
            
            df = pd.merge(df_v, df_m, on='ns_link', how='inner')

            # Alerta de Vendas não vinculadas
            ns_perdidos = set(df_v['ns_link'].unique()) - set(df_m['ns_link'].unique())
            if ns_perdidos and st.session_state.perfil == "admin":
                st.warning(f"⚠️ Existem vendas para os seguintes NS não vinculados: {', '.join(ns_perdidos)}")

            if not df.empty:
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df['pl_adj'] = df['plano'].astype(str).str.lower().replace('crédito', 'à vista')
                df_t_c = df_t.drop_duplicates(subset=['id_plano', 'bandeira', 'meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')

                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0)
                df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0.0)
                df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                c1, c2, c3 = st.columns(3)
                c1.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                c2.metric("Líquido Total", f"R$ {df['liq'].sum():,.2f}")
                c3.metric("Vendas", len(df))
                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq']], use_container_width=True)
            else:
                st.info("Nenhuma venda vinculada para este dia.")

st.sidebar.caption("MJ Soluções v139.0")
