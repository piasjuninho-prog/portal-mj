import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date

st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

def limpar(val):
    return str(val).strip().upper().lstrip('0') if val else ""

if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMIN"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("Erro")
else:
    menu = st.sidebar.radio("Menu", ["Dashboard", "Gestão", "Vincular", "Sair"])
    if menu == "Sair": st.session_state.perfil = None; st.rerun()

    if menu == "Vincular":
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vin"):
            c, ns, pl = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data]), st.text_input("NS"), st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular"):
                for n in [limpar(x) for x in ns.split(",") if x.strip() != ""]:
                    conn.table("maquinas_ns").upsert({"ns": n, "nome_lojista": c, "nome_plano": pl}).execute()
                st.success("OK")

    elif menu == "Dashboard":
        st.title("📊 Dashboard")
        d_sel = st.sidebar.date_input("Data", date(2026, 7, 11))
        
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        
        if v_res.data and m_res.data:
            df_v, df_m = pd.DataFrame(v_res.data), pd.DataFrame(m_res.data)
            
            df_v['dt_v'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt_v'].dt.date == d_sel]
            
            df_v['link'] = df_v['ns'].apply(limpar)
            df_m['link'] = df_m['ns'].apply(limpar)
            
            df = pd.merge(df_v, df_m, on='link', how='inner')
            
            if not df.empty:
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                st.metric("Total Bruto", f"R$ {df['bruto_v'].sum():,.2f}")
                st.dataframe(df[['data_venda', 'nome_lojista', 'bruto_v']], use_container_width=True)
            else:
                st.info("Nenhuma venda vinculada encontrada para este dia.")
