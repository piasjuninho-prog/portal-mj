import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- INICIALIZAÇÃO DE MEMÓRIA DO SISTEMA ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'usuario' not in st.session_state: st.session_state.usuario = ""
if 'perfil' not in st.session_state: st.session_state.perfil = None

# --- CONEXÃO COM O BANCO DE DADOS ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# --- CONSTANTES ---
MOD_CARTAO = ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard", "pix"]

def limpar_ns(val):
    if not val: return ""
    import re
    # Remove qualquer caractere que não seja letra ou número e limpa zeros à esquerda
    return re.sub(r'[^A-Z0-9]', '', str(val).strip().upper().lstrip('0'))

# --- SISTEMA DE LOGIN ---
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
            try:
                res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
                if res.data and p == str(res.data[0].get('senha', '12345')):
                    st.session_state.auth = True
                    st.session_state.perfil = "cliente"
                    st.session_state.usuario = res.data[0]['nome_fantasia']
                    st.rerun()
                else: 
                    st.error("❌ Acesso Negado: Usuário ou senha incorretos.")
            except:
                st.error("Erro de conexão com o servidor.")
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    
    # Carrega lista de clientes para filtros e gestão
    res_est = conn.table("estabelecimentos").select("nome_fantasia").execute()
    todos_lojistas = sorted([e['nome_fantasia'] for e in res_est.data]) if res_est.data else []

    if st.session_state.perfil == "admin":
        st.sidebar.subheader("Filtros Dashboard")
        esc_lojistas = st.sidebar.multiselect("Filtrar Lojistas:", todos_lojistas, default=todos_lojistas)
        d_sel = st.sidebar.date_input("Data do Filtro", date.today())
        st.sidebar.divider()
        menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    else:
        esc_lojistas = [st.session_state.usuario]
        d_sel = st.sidebar.date_input("Data do Filtro", date.today())
        menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "🚪 Sair"])
    
    if menu == "🚪 Sair":
        st.session_state.auth = False
        st.rerun()

    # --- ABA GESTÃO (CADASTRAR E EXCLUIR CLIENTES) ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão de Clientes")
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("➕ CADASTRAR NOVO"):
                with st.form("add_c"):
                    n = st.text_input("Nome Fantasia")
                    e = st.text_input("Email")
                    if st.form_submit_button("Salvar Estabelecimento"):
                        if n and e:
                            conn.table("estabelecimentos").insert({"nome_fantasia": n.upper().strip(), "email": e.lower().strip(), "senha": "12345"}).execute()
                            st.success("✅ Cadastrado!")
                            st.rerun()
        with col2:
            with st.expander("🗑️ EXCLUIR CLIENTE"):
                if todos_lojistas:
                    rem = st.selectbox("Selecione para remover:", todos_lojistas)
                    if st.button("❌ Confirmar Exclusão"):
                        conn.table("estabelecimentos").delete().eq("nome_fantasia", rem).execute()
                        st.warning(f"Estabelecimento {rem} removido.")
                        st.rerun()
        
        st.write("---")
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- ABA PLANOS (GESTÃO DE TAXAS E CUSTOS) ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        t1, t2 = st.tabs(["📋 Visualizar", "⚙️ Criar/Editar"])
        res_p = conn.table("planos_mj").select("*").execute()
        lista_p = sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else []
        
        with t1:
            if lista_p:
                ps = st.selectbox("Escolha o Plano:", lista_p)
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_v = pd.DataFrame(res_t.data)
                    df_v['%'] = df_v['taxa_decimal'].apply(lambda x: f"{x*100:.2f}%")
                    st.write("### Grade de Taxas do Cliente")
                    st.dataframe(pd.pivot_table(df_v, values='%', index='meio', columns='bandeira', aggfunc='first').fillna("-"), use_container_width=True)
        
        with t2:
            modo = st.radio("Ação:", ["Novo Plano", "Editar Existente"], horizontal=True)
            nome_f = st.selectbox("Selecione o Plano:", lista_p) if modo == "Editar" else st.text_input("Nome do Plano")
            band_s = st.selectbox("Selecione a Bandeira:", ORDEM_BANDEIRAS)
            # Lógica inteligente para Pix vs Cartão
            mods = ["pix"] if band_s == "pix" else MOD_CARTAO
            df_ed = st.data_editor(pd.DataFrame({"Meio": mods, "Taxa Cliente (%)": 0.0, "Custo (%)": 0.0}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira no Plano"):
                if nome_f:
                    p_res = conn.table("planos_mj").upsert({"nome_plano": nome_f.upper().strip()}, on_conflict="nome_plano").execute()
                    id_f = p_res.data[0]['id']
                    conn.table("taxas_dos_planos").delete().eq("id_plano", id_f).eq("bandeira", band_s).execute()
                    batch = [{"id_plano": id_f, "bandeira": band_s, "meio": r['Meio'], "taxa_decimal": float(r['Taxa Cliente (%)'])/100, "custo_decimal": float(r['Custo (%)'])/100} for _, r in df_ed.iterrows()]
                    conn.table("taxas_dos_planos").insert(batch).execute()
                    st.success("✅ Taxas salvas!"); st.rerun()

    # --- ABA VINCULAR (NS PARA CLIENTE) ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina")
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vinc"):
            c = st.selectbox("Selecione o Cliente", todos_lojistas)
            ns = st.text_area("Números de Série (NS) - separe por vírgula")
            pl = st.selectbox("Plano de Taxas Ativo", sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else ["PADRAO"])
            if st.form_submit_button("Confirmar Vínculo"):
                for n in ns.split(","):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar_ns(n), "nome_lojista": c, "nome_plano": pl}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute()
                st.success("✅ Máquinas vinculadas com sucesso!")

    # --- ABA DASHBOARD (CORAÇÃO DO SISTEMA) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="auto_refresh_dashboard")
        st.title("📊 Dashboard Financeiro")
        
        # Coleta de Dados das 4 Tabelas Principais
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})
            
            # Filtro Data e Link NS
            df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt'].dt.date == d_sel]
            df_v['link'], df_m['link'] = df_v['ns'].apply(limpar_ns), df_m['ns'].apply(limpar_ns)
            
            # Junção Transparente (Left Join) para não sumir com vendas não vinculadas
            df = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='left')
            df['nome_lojista'] = df['nome_lojista'].fillna("⚠️ NÃO VINCULADO")

            # Aplica Filtro Sidebar Lojistas
            df = df[df['nome_lojista'].isin(esc_lojistas)]

            if not df.empty:
                # Cruzamento com Tabelas de Taxas
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df['pl_adj'] = df['plano'].astype(str).str.lower().replace('crédito','à vista').apply(lambda x: x + "x" if "em " in x and not x.endswith("x") else x)
                df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                
                # Cálculos Financeiros (Fórmula de Spread)
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                df['t_cus'] = pd.to_numeric(df.get('custo_decimal', 0), errors='coerce').fillna(0)
                
                df['liq_v'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                df['lucro_v'] = (df['bruto_v'] * (df['t_cli'] - df['t_cus'])).round(2)
                df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                # Cards de Resumo (KPIs)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Bruto Total", f"R$ {df['bruto_v'].sum():,.2f}")
                c2.metric("Líquido Total", f"R$ {df['liq_v'].sum():,.2f}")
                c3.metric("Vendas Totais", len(df))
                if st.session_state.perfil == "admin":
                    c4.metric("Lucro MJ Real", f"R$ {df['lucro_v'].sum():,.2f}")
                
                st.divider()
                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)
                
                # Alerta de Máquinas Órfãs
                perdidos = df[df['nome_lojista'] == "⚠️ NÃO VINCULADO"]['link'].unique()
                if len(perdidos) > 0: st.warning(f"🚨 Existem vendas para NS não cadastrados: {', '.join(perdidos)}")
            else:
                st.info("Nenhuma venda encontrada para os filtros selecionados.")
        else:
            st.error("Banco de dados de vendas está vazio.")

st.sidebar.caption("MJ Soluções v205.0")
