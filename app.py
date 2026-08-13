import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
import re

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO COM BANCO DE DADOS ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# --- CONSTANTES ---
ORDEM_MODALIDADES = ["pix", "débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard", "pix", "picpay"]

def limpar_ns(val):
    """Limpa NS mantendo letras e números (Essencial para terminais J9B do PagBank)"""
    if not val: return ""
    # Mantém letras e números, remove espaços e zeros à esquerda
    res = re.sub(r'[^A-Z0-9]', '', str(val).strip().upper()).lstrip('0')
    return res if res else "0"

# --- CONTROLE DE ACESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'usuario' not in st.session_state: st.session_state.usuario = ""
if 'perfil' not in st.session_state: st.session_state.perfil = None

if not st.session_state.auth:
    st.title("🔐 Login MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123": 
            st.session_state.auth = True; st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.auth = True; st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Credenciais inválidas.")
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    res_est = conn.table("estabelecimentos").select("nome_fantasia").execute()
    todos_lojistas = sorted([e['nome_fantasia'] for e in res_est.data]) if res_est.data else []

    if st.session_state.perfil == "admin":
        st.sidebar.subheader("Filtros Dashboard")
        # Força inclusão do 'Não Vinculado' para o Admin ver o que está sumido
        esc_lojistas = st.sidebar.multiselect("Filtrar Lojistas:", ["⚠️ NÃO VINCULADO"] + todos_lojistas, default=["⚠️ NÃO VINCULADO"] + todos_lojistas)
        d_sel = st.sidebar.date_input("Data do Filtro", date.today())
        st.sidebar.divider()
        menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    else:
        esc_lojistas = [st.session_state.usuario]
        d_sel = st.sidebar.date_input("Data do Filtro", date.today())
        menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "🚪 Sair"])
    
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- ABA GESTÃO ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        c1, c2 = st.columns(2)
        with c1:
            with st.expander("➕ CADASTRAR NOVO"):
                with st.form("add"):
                    n, e = st.text_input("Nome Fantasia"), st.text_input("Email")
                    if st.form_submit_button("Salvar"):
                        conn.table("estabelecimentos").insert({"nome_fantasia": n.upper().strip(), "email": e.lower().strip(), "senha": "12345"}).execute()
                        st.success("✅ Cadastrado!"); st.rerun()
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina/Terminal")
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vinc"):
            c = st.selectbox("Cliente", todos_lojistas)
            ns_txt = st.text_area("Números de Série / IDs Terminal (Ex: 173... ou J9B...)")
            pl = st.selectbox("Plano", sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else ["PADRAO"])
            if st.form_submit_button("Salvar Vínculo"):
                for n in ns_txt.split(","):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar_ns(n), "nome_lojista": c, "nome_plano": pl}).execute()
                st.success("✅ Vinculado com sucesso!")

    # --- ABA DASHBOARD (v214.0 - ANTI-ERRO) ---
    elif menu == "🏠 Dashboard":
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=60000, key="refresh_v214")
        st.title("📊 Dashboard Financeiro")
        
        # 1. Coleta Dados
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})
            
            # --- TRATAMENTO DATA ---
            df_v['dt_limpa'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce').dt.date
            
            # Filtro de data ANTES do merge para ganhar velocidade
            df_v = df_v[df_v['dt_limpa'] == d_sel].copy()
            
            if not df_v.empty:
                # --- VÍNCULO ---
                df_v['link'] = df_v['ns'].apply(limpar_ns)
                df_m['link'] = df_m['ns'].apply(limpar_ns)
                
                # LEFT JOIN: Nunca apaga vendas da tela
                df = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='left')
                df['nome_lojista'] = df['nome_lojista'].fillna("⚠️ NÃO VINCULADO")
                
                # Barra de Status
                st.success(f"📦 Encontradas {len(df)} vendas no banco para esta data.")

                # Filtro Sidebar Lojista
                df = df[df['nome_lojista'].isin(esc_lojistas)]

                if not df.empty:
                    # Cruzamento Taxas
                    df = pd.merge(df, df_p, on='nome_plano', how='left')
                    def norm_pl(row):
                        p = str(row['plano']).lower()
                        if 'débito' in p: return 'débito'
                        if 'pix' in p or str(row['bandeira']).lower() == 'pix': return 'pix'
                        m = re.findall(r'\d+', p)
                        return f"em {m[0]}x" if m else 'à vista'
                    df['pl_adj'] = df.apply(norm_pl, axis=1)
                    
                    df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                    df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                    
                    df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                    df['liq_v'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                    df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                    # Mostra os Cards
                    st.divider()
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Bruto (Filtrado)", f"R$ {df['bruto_v'].sum():,.2f}")
                    k2.metric("Líquido Total", f"R$ {df['liq_v'].sum():,.2f}")
                    k3.metric("Vendas Exibidas", len(df))
                    
                    st.dataframe(df[['data_venda', 'nome_lojista', 'adquirente', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)
                else:
                    st.warning("Nenhuma venda encontrada para os lojistas selecionados na barra lateral.")
            else:
                st.info(f"O banco de dados não possui vendas registradas no dia {d_sel.strftime('%d/%m/%Y')}.")
        else:
            st.error("O banco de dados de vendas está completamente vazio.")

st.sidebar.caption("MJ Soluções v214.0")
