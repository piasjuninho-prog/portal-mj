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

# Constantes
ORDEM_MODALIDADES = ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard"]

def limpar_ns(val): 
    return str(val).strip().upper().lstrip('0') if val else ""

# --- LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 Login MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123": 
            st.session_state.auth = True
            st.session_state.perfil = "admin"
            st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.auth = True
                st.session_state.perfil = "cliente"
                st.session_state.usuario = res.data[0]['nome_fantasia']
                st.rerun()
            else: 
                st.error("Acesso Negado")
else:
    # --- BARRA LATERAL (FILTROS SEMPRE NO TOPO) ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    
    # 1. Busca lista de clientes para os filtros
    res_est = conn.table("estabelecimentos").select("nome_fantasia").execute()
    todos_clientes = sorted([e['nome_fantasia'] for e in res_est.data]) if res_est.data else []

    st.sidebar.subheader("Filtros")
    if st.session_state.perfil == "admin":
        # FILTRO DE CLIENTES QUE TINHA SUMIDO:
        esc_lojistas = st.sidebar.multiselect("Filtrar Lojistas:", todos_clientes, default=todos_clientes)
    else:
        esc_lojistas = [st.session_state.usuario]
    
    d_sel = st.sidebar.date_input("Data do Filtro", date.today())
    
    st.sidebar.divider()
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"], key="nav_menu_main")
    
    if menu == "🚪 Sair":
        st.session_state.auth = False
        st.rerun()

    # --- ABA GESTÃO ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        c1, c2 = st.columns(2)
        with c1:
            with st.expander("➕ CADASTRAR NOVO"):
                with st.form("add"):
                    n = st.text_input("Nome Fantasia")
                    e = st.text_input("Email")
                    if st.form_submit_button("Salvar"):
                        conn.table("estabelecimentos").insert({"nome_fantasia": n.upper(), "email": e.lower(), "senha": "12345"}).execute()
                        st.rerun()
        with c2:
            with st.expander("🗑️ EXCLUIR"):
                if todos_clientes:
                    excluir = st.selectbox("Escolha para apagar", todos_clientes)
                    if st.button("Confirmar Exclusão"):
                        conn.table("estabelecimentos").delete().eq("nome_fantasia", excluir).execute()
                        st.rerun()
        
        st.write("---")
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina")
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("form_vinc"):
            c = st.selectbox("Selecione o Cliente", todos_clientes)
            ns_txt = st.text_area("Números de Série (NS)")
            pl = st.selectbox("Plano de Taxas", sorted([p['nome_plano'] for p in res_p.data]))
            if st.form_submit_button("✅ Salvar Vínculo"):
                import re
                for n in re.split(r'[,\n\s]+', ns_txt):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar_ns(n), "nome_lojista": c, "nome_plano": pl}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute()
                st.success("Vinculado!"); st.rerun()

    # --- ABA DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="refresh_dash_pro")
        st.title("📊 Dashboard Financeiro")
        
        # Coleta de Dados
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data and m_res.data:
            df_v, df_m = pd.DataFrame(v_res.data), pd.DataFrame(m_res.data)
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})

            df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt'].dt.date == d_sel]
            df_v['link'], df_m['link'] = df_v['ns'].apply(limpar_ns), df_m['ns'].apply(limpar_ns)
            
            # Cruzamento
            df = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='inner', suffixes=('', '_m'))
            
            # Aplica o filtro de lojistas selecionados na lateral
            df = df[df['nome_lojista'].isin(esc_lojistas)]

            if not df.empty:
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df['pl_adj'] = df['plano'].astype(str).str.lower().replace('crédito','à vista').apply(lambda x: x + "x" if "em " in x and not x.endswith("x") else x)
                df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                
                # Cálculos
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                df['t_cus'] = pd.to_numeric(df.get('custo_decimal', 0), errors='coerce').fillna(0)
                df['liq_v'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                df['lucro_v'] = (df['bruto_v'] * (df['t_cli'] - df['t_cus'])).round(2)
                df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Bruto", f"R$ {df['bruto_v'].sum():,.2f}")
                c2.metric("Líquido", f"R$ {df['liq_v'].sum():,.2f}")
                c3.metric("Vendas", len(df))
                c4.metric("Lucro MJ", f"R$ {df['lucro_v'].sum():,.2f}")
                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)
            else:
                st.info("Nenhuma venda encontrada para os filtros selecionados.")
        else:
            st.info("Sincronize as vendas para ver os dados.")

st.sidebar.caption("MJ Soluções v190.0")
