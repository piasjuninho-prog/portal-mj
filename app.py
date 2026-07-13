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
    st.title("🔐 Portal MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("Login inválido.")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Gestão", "👤 Vincular", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    if menu == "🏫 Gestão":
        res = conn.table("estabelecimentos").select("*").execute()
        st.data_editor(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    elif menu == "👤 Vincular":
        st.subheader("👤 Vincular Máquina")
        res_e, res_p = conn.table("estabelecimentos").select("nome_fantasia").execute(), conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vin"):
            c, ns, pl = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data]), st.text_input("NS"), st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular"):
                for n in [limpar_ns(x) for x in ns.split(",") if x.strip() != ""]:
                    conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                st.success("Vinculado!")

    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="refresh")
        st.title("📊 Dashboard MJ Financeiro")
        d_sel = st.sidebar.date_input("Data do Filtro", date(2026, 7, 11))

        # BUSCA DADOS BRUTOS (Sem filtros iniciais para evitar erros)
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        
        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista'])

            # Limpeza de data e NS
            df_v['dt_limpa'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v['link'] = df_v['ns'].apply(limpar_ns)
            df_m['link'] = df_m['ns'].apply(limpar_ns)

            # Filtra vendas pela data do Dashboard
            vendas_do_dia = df_v[df_v['dt_limpa'].dt.date == d_sel].copy()

            if not vendas_do_dia.empty:
                # Cruzamento LEFT JOIN (Para não sumir com nada do banco)
                df = pd.merge(vendas_do_dia, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='left')
                df['nome_lojista'] = df['nome_lojista'].fillna("⚠️ NÃO VINCULADO")
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)

                # Mostra aviso se houver algo não vinculado
                if "⚠️ NÃO VINCULADO" in df['nome_lojista'].values:
                    ns_soltos = df[df['nome_lojista'] == "⚠️ NÃO VINCULADO"]['link'].unique()
                    st.warning(f"Existem {len(ns_soltos)} máquinas não vinculadas: {', '.join(ns_soltos)}")

                # KPIs
                c1, c2 = st.columns(2)
                c1.metric("Bruto Total (Dia)", f"R$ {df['bruto_v'].sum():,.2f}")
                c2.metric("Qtd Vendas", len(df))

                st.divider()
                st.write("### Listagem de Vendas no Banco de Dados")
                st.dataframe(df[['data_venda', 'nome_lojista', 'bruto', 'ns', 'adquirente']], use_container_width=True)
            else:
                st.info(f"O banco de dados não retornou vendas para o dia {d_sel}. Verifique se o robô sincronizou com sucesso.")
        else:
            st.error("O banco de dados de vendas está vazio.")

st.sidebar.caption("MJ Soluções v148.0")
