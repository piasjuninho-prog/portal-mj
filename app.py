import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ PAG", layout="wide", initial_sidebar_state="expanded")

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

# --- 2. LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG - Acesso")
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
    # --- 3. MENU LATERAL ---
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 4. 🏫 SEÇÃO: GESTÃO DE CLIENTES (ARRUMADO!) ---
    if menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        
        # Criamos as duas abas: uma para ver a lista e outra para cadastrar
        tab_lista, tab_novo = st.tabs(["📋 Lista de Clientes", "➕ Novo Cadastro"])

        with tab_novo:
            st.subheader("Cadastrar Novo Estabelecimento")
            with st.form("form_novo_est", clear_on_submit=True):
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Nome Fantasia (Nome no Robô)")
                novo_doc = c2.text_input("CNPJ ou CPF")
                
                c3, c4 = st.columns(2)
                novo_email = c3.text_input("E-mail de Login")
                nova_senha = c4.text_input("Senha de Acesso", value="12345")
                
                novo_adq = st.selectbox("Adquirente", ["InfinitePay", "PicPay", "Stone", "Stone", "PagSeguro"])
                
                if st.form_submit_button("💾 Salvar Estabelecimento", use_container_width=True):
                    if novo_nome and novo_email:
                        try:
                            conn.table("estabelecimentos").insert({
                                "nome_fantasia": novo_nome.upper().strip(),
                                "email": novo_email.lower().strip(),
                                "cnpj_cpf": novo_doc,
                                "adquirente": novo_adq,
                                "senha": nova_senha
                            }).execute()
                            st.success(f"✅ Cliente {novo_nome} cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                    else:
                        st.warning("⚠️ Preencha o Nome e o E-mail.")

        with tab_lista:
            st.subheader("Clientes Cadastrados")
            res_e = conn.table("estabelecimentos").select("*").execute()
            if res_e.data:
                df_e = pd.DataFrame(res_e.data)
                # Tabela editável para correções rápidas
                df_ed = st.data_editor(
                    df_e, 
                    column_order=("nome_fantasia", "email", "senha", "adquirente", "nome_plano_ativo"),
                    use_container_width=True, 
                    hide_index=True
                )
                
                if st.button("💾 Salvar Alterações na Lista"):
                    for _, r in df_ed.iterrows():
                        conn.table("estabelecimentos").update({
                            "nome_fantasia": str(r["nome_fantasia"]).upper(),
                            "email": str(r["email"]).lower(),
                            "senha": str(r["senha"]),
                            "adquirente": r["adquirente"]
                        }).eq("id", r["id"]).execute()
                    st.success("✅ Dados atualizados!")
                    st.rerun()
            else:
                st.info("Nenhum cliente cadastrado ainda.")

    # --- 5. 📂 SEÇÃO: PLANOS ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        t_ver, t_criar = st.tabs(["📋 Meus Planos", "➕ Criar Novo"])
        
        with t_ver:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                p_s = st.selectbox("Escolha o Plano:", [p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_s)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)

        with t_criar:
            nome_p = st.text_input("Nome do Plano (Ex: VIP 12X)")
            band_s = st.selectbox("Configurar Bandeira:", ORDEM_BANDEIRAS)
            df_setup = pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo Adquirente (%)": [0.0]*13})
            df_ed_p = st.data_editor(df_setup, use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira no Plano"):
                res = conn.table("planos_mj").select("*").eq("nome_plano", nome_p.upper().strip()).execute()
                if not res.data: res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper().strip()}).execute()
                id_p = res.data[0]['id']
                batch = [{"id_plano": id_p, "bandeira": band_s, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo Adquirente (%)']/100} for _, r in df_ed_p.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Taxas Salvas!"); st.rerun()

    # --- 6. 👤 SEÇÃO: VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Plano ao Cliente")
        res_p = conn.table("planos_mj").select("id, nome_plano").execute()
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        if res_p.data and res_e.data:
            with st.form("vin_form"):
                c_s = st.selectbox("Selecione o Cliente", [e['nome_fantasia'] for e in res_e.data])
                p_s = st.selectbox("Selecione o Plano", [p['nome_plano'] for p in res_p.data])
                if st.form_submit_button("✅ Confirmar Vínculo"):
                    conn.table("estabelecimentos").update({"nome_plano_ativo": p_s}).eq("nome_fantasia", c_s).execute()
                    st.success(f"Vínculo realizado com sucesso!")
        else: st.warning("Cadastre clientes e planos primeiro.")

    # --- 7. 🏠 DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # Puxa dados da View que contém os cálculos
            df = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            if not df.empty:
                df['data_dt'] = df['data_venda'].apply(converter_data)
                df = df.dropna(subset=['data_dt'])
                df['lojista'] = df['lojista'].astype(str)

                # Filtros Sidebar
                st.sidebar.subheader("Filtros")
                l_filt = sorted(df['lojista'].unique())
                if st.session_state.perfil == "admin":
                    esc = st.sidebar.multiselect("Lojistas:", l_filt, default=l_filt)
                    df = df[df['lojista'].isin(esc)]
                else: df = df[df['lojista'] == st.session_state.usuario]

                d_ini = st.sidebar.date_input("Início", date(datetime.now().year, datetime.now().month, 1))
                d_fim = st.sidebar.date_input("Fim", datetime.now().date())
                df = df[(df['data_dt'].dt.date >= d_ini) & (df['data_dt'].dt.date <= d_fim)]

                if not df.empty:
                    # Garantir números
                    for c in ['bruto', 'liquido_cliente', 'spread_rs']:
                        df[c] = pd.to_numeric(df.get(c, 0.0), errors='coerce').fillna(0.0)

                    st.title(f"📊 Dashboard Geral MJ")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}")
                    c2.metric("Líquido Esperado", f"R$ {df['liquido_cliente'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    if st.session_state.perfil == "admin": 
                        c4.metric("Seu Lucro", f"R$ {df['spread_rs'].sum():,.2f}")
                    
                    st.divider()
                    st.dataframe(df[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
            else: st.info("Sem vendas sincronizadas.")
        except Exception as e: st.error(f"Aguardando dados... ({e})")
