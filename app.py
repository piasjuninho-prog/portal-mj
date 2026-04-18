import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ PAG", layout="wide", initial_sidebar_state="expanded")

# --- 1. CONEXÃO DIRETA (CORRIGIDO PARA NÃO DAR ERRO) ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Listas de ordenação fixa
ORDEM_MODALIDADES = ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard"]

# Função para converter data
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
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif p == "12345":
            st.session_state.perfil = "cliente"; st.session_state.usuario = u
            st.rerun()
        else: st.error("❌ Acesso negado.")
else:
    # --- 3. MENU LATERAL ---
    opcoes_menu = ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    st.sidebar.markdown(f"""<div style="background:#f0f2f6;padding:10px;border-radius:5px;border-left:5px solid #2ecc71;">
        <small>🔄 <b>Sincronizado:</b> {datetime.now().strftime('%H:%M:%S')}</small></div>""", unsafe_allow_html=True)
    
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes_menu)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 4. ABA: ESTABELECIMENTOS ---
    if menu == "🏫 Estabelecimentos" and st.session_state.perfil == "admin":
        st.title("🏫 Gestão de Estabelecimentos")
        tab_list, tab_cad = st.tabs(["📋 Lista de Clientes", "➕ Novo Cadastro"])
        with tab_cad:
            with st.form("cad_estabelecimento", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nome_f = c1.text_input("Nome Fantasia / Nome no Robô")
                doc = c2.text_input("CNPJ ou CPF")
                c_adq, c_prov = st.columns(2)
                adq = c_adq.selectbox("Adquirente", ["InfinitePay", "PicPay", "Stone", "PagSeguro", "Outra"])
                prov = c_prov.text_input("Provedor", placeholder="Ex: MJ PAG")
                tel = st.text_input("Telefone")
                if st.form_submit_button("💾 Salvar Estabelecimento"):
                    if nome_f:
                        conn.table("estabelecimentos").insert({"nome_fantasia": nome_f.upper().strip(), "cnpj_cpf": doc, "adquirente": adq, "provedor": prov.upper(), "telefone": tel}).execute()
                        st.success("Cadastrado com sucesso!")
                    else: st.error("Nome é obrigatório.")
        with tab_list:
            res_est = conn.table("estabelecimentos").select("*").execute()
            if res_est.data:
                st.dataframe(pd.DataFrame(res_est.data)[['nome_fantasia', 'cnpj_cpf', 'adquirente', 'provedor', 'nome_plano_ativo']], use_container_width=True)

    # --- 5. ABA: CRIAR / CONSULTAR PLANOS ---
    elif menu == "📂 Criar Planos" and st.session_state.perfil == "admin":
        st.title("📂 Gestão de Planos de Taxas")
        tab_view, tab_new = st.tabs(["📋 Meus Planos", "➕ Criar Novo Plano"])
        with tab_view:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                planos_nomes = [p['nome_plano'] for p in res_p.data]
                plano_sel = st.selectbox("Selecione um plano para visualizar:", options=planos_nomes)
                id_plano_sel = next(p['id'] for p in res_p.data if p['nome_plano'] == plano_sel)
                res_taxas_view = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_plano_sel).execute()
                if res_taxas_view.data:
                    df_view = pd.DataFrame(res_taxas_view.data)
                    df_pivot = df_view.pivot(index='meio', columns='bandeira', values='taxa_decimal')
                    df_pivot = df_pivot.reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    df_pivot.columns = [c.capitalize() for c in df_pivot.columns]
                    st.write(f"### Taxas do Plano: {plano_sel}")
                    st.dataframe(df_pivot.applymap(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
        with tab_new:
            st.subheader("📑 Criando Novo Plano")
            nome_plano = st.text_input("Nome do Plano", placeholder="Ex: VIP 12X")
            df_setup = pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Mastercard (%)": [0.0]*13, "Visa (%)": [0.0]*13, "Elo (%)": [0.0]*13, "Amex (%)": [0.0]*13, "Hipercard (%)": [0.0]*13})
            df_editado = st.data_editor(df_setup, use_container_width=True, hide_index=True)
            if st.button("🚀 SALVAR PLANO COMPLETO"):
                if nome_plano:
                    res = conn.table("planos_mj").insert({"nome_plano": nome_plano.upper()}).execute()
                    id_p = res.data[0]['id']
                    taxas_batch = []
                    b_map = {"Mastercard (%)": "mastercard", "Visa (%)": "visa", "Elo (%)": "elo", "Amex (%)": "amex", "Hipercard (%)": "hipercard"}
                    for _, row in df_editado.iterrows():
                        for col, band in b_map.items():
                            taxas_batch.append({"id_plano": id_p, "bandeira": band, "meio": row['Modalidade'], "taxa_decimal": row[col]/100})
                    conn.table("taxas_dos_planos").insert(taxas_batch).execute()
                    st.success("Plano Criado!")
                    st.rerun()

    # --- 6. ABA: VINCULAR CLIENTE ---
    elif menu == "👤 Vincular Cliente" and st.session_state.perfil == "admin":
        st.title("👤 Associar Estabelecimento a um Plano")
        res_p = conn.table("planos_mj").select("id, nome_plano").execute()
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        if res_p.data and res_e.data:
            dict_planos = {p['nome_plano']: p['id'] for p in res_p.data}
            lista_clientes = sorted([e['nome_fantasia'] for e in res_e.data])
            with st.form("form_vinculo"):
                cliente_sel = st.selectbox("Selecione o Estabelecimento", options=lista_clientes)
                ns_input = st.text_input("NS da Maquininha (Para vários, separe por vírgula)")
                plano_sel = st.selectbox("Selecione o Plano", options=list(dict_planos.keys()))
                if st.form_submit_button("✅ FINALIZAR VÍNCULO", use_container_width=True):
                    id_p = dict_planos[plano_sel]
                    res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                    lista_ns = [n.strip() for n in ns_input.split(",")]
                    novas_taxas = []
                    for ns in lista_ns:
                        for t in res_t.data:
                            novas_taxas.append({"cliente": cliente_sel, "ns": ns, "bandeira": t['bandeira'], "meio": t['meio'], "taxa_decimal": t['taxa_decimal']})
                    conn.table("taxas_clientes").insert(novas_taxas).execute()
                    conn.table("estabelecimentos").update({"nome_plano_ativo": plano_sel}).eq("nome_fantasia", cliente_sel).execute()
                    st.success(f"Vínculo realizado!")

    # --- 7. ABA: DASHBOARD ---
    elif menu in ["🏠 Dashboard"]:
        st_autorefresh(interval=30000, key="refresh")
        try:
            df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            if not df_v.empty:
                df_v = df_v[df_v['lojista'].notna() & (df_v['lojista'].astype(str).str.lower() != 'nan')].copy()
                df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
                df_v = df_v.dropna(subset=['data_dt'])
                if st.session_state.perfil == "admin":
                    st.title("👨‍✈️ Painel Geral MJ")
                    lista_lj = sorted([str(x) for x in df_v['lojista'].unique() if x])
                    escolha = st.sidebar.multiselect("Filtrar Lojistas:", options=lista_lj, default=lista_lj)
                    v_c = df_v[df_v['lojista'].isin(escolha)].copy()
                else:
                    st.title(f"🏠 Painel: {st.session_state.usuario}")
                    v_c = df_v[df_v['lojista'] == st.session_state.usuario].copy()
                st.sidebar.divider()
                d_ini = st.sidebar.date_input("Início", v_c['data_dt'].min().date() if not v_c.empty else datetime.now().date())
                d_fim = st.sidebar.date_input("Fim", v_c['data_dt'].max().date() if not v_c.empty else datetime.now().date())
                v_c = v_c[(v_c['data_dt'].dt.date >= d_ini) & (v_c['data_dt'].dt.date <= d_fim)]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}")
                m2.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
                m3.metric("Qtd Vendas", len(v_c))
                if st.session_state.perfil == "admin":
                    m4.metric("Seu Lucro (R$)", f"R$ {v_c['spread_rs'].sum():,.2f}")
                st.write("---")
                st.dataframe(v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
            else: st.info("Sem vendas.")
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções Comercial v14.0")
