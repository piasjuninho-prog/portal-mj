import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- MEMÓRIA ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'perfil' not in st.session_state: st.session_state.perfil = None

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

def limpar_ns(val):
    if not val: return ""
    import re
    return re.sub(r'[^A-Z0-9]', '', str(val).strip().upper().lstrip('0'))

# --- LOGIN ---
if not st.session_state.auth:
    st.title("🔐 Login MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123": 
            st.session_state.auth = True; st.session_state.perfil = "admin"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.auth = True; st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Acesso Negado")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # ABAS GESTÃO, PLANOS E VINCULAR
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão")
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)

    elif menu == "👤 Vincular":
        st.title("👤 Vincular Nova Máquina")
        res_e, res_p = conn.table("estabelecimentos").select("nome_fantasia").execute(), conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vinc"):
            c = st.selectbox("Cliente", sorted([e['nome_fantasia'] for e in res_e.data]))
            ns_input = st.text_area("Copie os NS da tabela de erro e cole aqui (separados por vírgula)")
            pl = st.selectbox("Escolha o Plano", sorted([p['nome_plano'] for p in res_p.data]))
            if st.form_submit_button("✅ Salvar Vínculo"):
                for n in ns_input.split(","):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar_ns(n), "nome_lojista": c, "nome_plano": pl}).execute()
                st.success("Máquinas vinculadas!"); st.rerun()

    # --- ABA DASHBOARD (v207.0 - DETECTOR DE VENDAS PERDIDAS) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="auto_ref_v207")
        st.title("📊 Dashboard")
        d_sel = st.sidebar.date_input("Data do Filtro", date(2026, 8, 11))
        
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()

        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})
            
            # Filtro Data e Link NS
            df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt'].dt.date == d_sel]
            df_v['link'], df_m['link'] = df_v['ns'].apply(limpar_ns), df_m['ns'].apply(limpar_ns)
            
            # --- MONITOR DE MÁQUINAS NÃO VINCULADAS ---
            df_check = pd.merge(df_v, df_m[['link', 'nome_lojista']], on='link', how='left')
            vendas_sem_dono = df_check[df_check['nome_lojista'].isna()]

            if not vendas_sem_dono.empty:
                st.error(f"🚨 ALERTA: Encontramos {len(vendas_sem_dono)} vendas no banco de dados sem vínculo!")
                st.write("Estes são os NS das máquinas que o robô sincronizou mas você não cadastrou no portal:")
                ns_perdidos = vendas_sem_dono.groupby('ns').agg({'bruto': 'sum', 'adquirente': 'first'}).reset_index()
                st.table(ns_perdidos)
                st.divider()

            # Cruzamento Principal (Só mostra o que tem dono)
            df = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='inner')

            if not df.empty:
                loj_ops = sorted(df['nome_lojista'].unique())
                if st.session_state.perfil == "admin":
                    esc_loj = st.sidebar.multiselect("Filtrar Lojistas:", loj_ops, default=loj_ops)
                    df = df[df['nome_lojista'].isin(esc_loj)]

                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df['pl_adj'] = df['plano'].astype(str).str.lower().replace('crédito','à vista').apply(lambda x: x + "x" if "em " in x and not x.endswith("x") else x)
                df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                df['liq_v'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                c1, c2, c3 = st.columns(3)
                c1.metric("Bruto (Vinculado)", f"R$ {df['bruto_v'].sum():,.2f}")
                c2.metric("Líquido Total", f"R$ {df['liq_v'].sum():,.2f}")
                c3.metric("Vendas Vinculadas", len(df))
                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)
            else:
                st.info("Nenhuma venda vinculada encontrada para hoje.")

st.sidebar.caption("MJ Soluções v207.0")
