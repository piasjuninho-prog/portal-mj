import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ PAG", layout="wide", initial_sidebar_state="expanded")

# --- 1. CONEXÃO ---
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

# --- 2. LOGIN POR E-MAIL ---
if 'perfil' not in st.session_state: st.session_state.perfil = None

if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG - Login")
    u = st.text_input("E-mail de Acesso").lower().strip() 
    p = st.text_input("Senha", type="password")
    
    if st.button("Entrar no Sistema", use_container_width=True):
        if u == "admin@mjpag.com" or (u == "ADMIN" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res_user = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res_user.data:
                dados_user = res_user.data[0]
                if p == str(dados_user.get('senha', '12345')):
                    st.session_state.perfil = "cliente"
                    st.session_state.usuario = dados_user['nome_fantasia']
                    st.rerun()
                else: st.error("❌ Senha incorreta.")
            else: st.error("❌ E-mail não encontrado.")
else:
    # --- 3. MENU LATERAL ---
    if st.session_state.perfil == "admin":
        opcoes_menu = ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"]
    else:
        opcoes_menu = ["🏠 Dashboard", "🚪 Sair"]

    st.sidebar.title(f"👤 {st.session_state.usuario}")
    st.sidebar.markdown(f"""<div style="background:#f0f2f6;padding:10px;border-radius:5px;border-left:5px solid #2ecc71;">
        <small>🔄 <b>Sincronizado:</b> {datetime.now().strftime('%H:%M:%S')}</small></div>""", unsafe_allow_html=True)
    
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes_menu)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 4. ABA: ESTABELECIMENTOS (COM CAMPO E-MAIL) ---
    if menu == "🏫 Estabelecimentos" and st.session_state.perfil == "admin":
        st.title("🏫 Gestão de Estabelecimentos")
        tab_list, tab_cad = st.tabs(["📋 Lista de Clientes", "➕ Novo Cadastro"])
        
        with tab_cad:
            with st.form("cad_estabelecimento", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nome_f = c1.text_input("Nome Fantasia (Ex: MJ INFINITE...)")
                doc = c2.text_input("CNPJ ou CPF")
                
                # ADICIONADO CAMPO DE EMAIL AQUI
                email_cli = st.text_input("E-mail de Login (Ex: cashday... @gmail.com)")
                
                c3, c4 = st.columns(2)
                adq = c3.selectbox("Adquirente", ["InfinitePay", "PicPay", "Stone", "PagSeguro"])
                prov = c4.text_input("Provedor", value="MJ PAG")
                senha_cli = st.text_input("Definir Senha", value="12345")
                
                if st.form_submit_button("💾 Salvar Novo Estabelecimento"):
                    if nome_f and email_cli:
                        conn.table("estabelecimentos").insert({
                            "nome_fantasia": nome_f.upper().strip(), 
                            "cnpj_cpf": doc, 
                            "email": email_cli.lower().strip(),
                            "adquirente": adq, "provedor": prov.upper(), "senha": senha_cli
                        }).execute()
                        st.success(f"✅ Cliente {nome_f} cadastrado com o e-mail {email_cli}!")
                    else: st.warning("⚠️ Nome Fantasia e E-mail são obrigatórios.")

        with tab_list:
            res_est = conn.table("estabelecimentos").select("*").execute()
            if res_est.data:
                df_est = pd.DataFrame(res_est.data)
                df_ed = st.data_editor(df_est, column_order=("nome_fantasia", "email", "senha", "adquirente", "provedor"), use_container_width=True, hide_index=True)
                if st.button("💾 Salvar Alterações"):
                    for i, r in df_ed.iterrows():
                        conn.table("estabelecimentos").update({"nome_fantasia": r["nome_fantasia"].upper(), "email": r["email"].lower(), "senha": r["senha"]}).eq("id", r["id"]).execute()
                    st.success("Dados atualizados!")

    # --- 5. ABA: CRIAR PLANOS ---
    elif menu == "📂 Criar Planos" and st.session_state.perfil == "admin":
        st.title("📂 Gestão de Planos")
        tab_view, tab_new = st.tabs(["📋 Meus Planos", "➕ Criar Novo"])
        with tab_view:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                p_sel = st.selectbox("Plano:", options=[p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_sel)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_piv = pd.DataFrame(res_t.data).pivot(index='meio', columns='bandeira', values='taxa_decimal').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
        with tab_new:
            nome_plano = st.text_input("Nome do Plano")
            df_setup = pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Mastercard (%)": [0.0]*13, "Visa (%)": [0.0]*13, "Elo (%)": [0.0]*13, "Amex (%)": [0.0]*13, "Hipercard (%)": [0.0]*13})
            df_ed = st.data_editor(df_setup, use_container_width=True, hide_index=True)
            if st.button("🚀 SALVAR PLANO"):
                res = conn.table("planos_mj").insert({"nome_plano": nome_plano.upper()}).execute()
                id_p = res.data[0]['id']
                batch = []
                b_map = {"Mastercard (%)": "mastercard", "Visa (%)": "visa", "Elo (%)": "elo", "Amex (%)": "amex", "Hipercard (%)": "hipercard"}
                for _, row in df_ed.iterrows():
                    for col, band in b_map.items():
                        batch.append({"id_plano": id_p, "bandeira": band, "meio": row['Modalidade'], "taxa_decimal": row[col]/100})
                conn.table("taxas_dos_planos").insert(batch).execute()
                st.success("Plano Criado!")

    # --- 6. ABA: VINCULAR CLIENTE ---
    elif menu == "👤 Vincular Cliente" and st.session_state.perfil == "admin":
        st.title("👤 Vincular Plano")
        res_p = conn.table("planos_mj").select("id, nome_plano").execute()
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        if res_p.data and res_e.data:
            d_p = {p['nome_plano']: p['id'] for p in res_p.data}
            l_c = sorted([e['nome_fantasia'] for e in res_e.data])
            with st.form("vinculo"):
                c_sel = st.selectbox("Estabelecimento", l_c)
                ns_in = st.text_input("NS (Separe por vírgula)")
                p_sel = st.selectbox("Plano", list(d_p.keys()))
                if st.form_submit_button("✅ FINALIZAR"):
                    res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", d_p[p_sel]).execute()
                    l_ns = [n.strip() for n in ns_in.split(",")]
                    novas = []
                    for ns in l_ns:
                        for t in res_t.data:
                            novas.append({"cliente": c_sel, "ns": ns, "bandeira": t['bandeira'], "meio": t['meio'], "taxa_decimal": t['taxa_decimal']})
                    conn.table("taxas_clientes").insert(novas).execute()
                    conn.table("estabelecimentos").update({"nome_plano_ativo": p_sel}).eq("nome_fantasia", c_sel).execute()
                    st.success("Vínculo realizado!")

    # --- 7. ABA: DASHBOARD ---
    elif menu in ["🏠 Dashboard"]:
        st_autorefresh(interval=30000, key="refresh")
        try:
            res_oficial = conn.table("estabelecimentos").select("nome_fantasia").execute()
            lista_oficial = [e['nome_fantasia'] for e in res_oficial.data]
            df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            if not df_v.empty:
                df_v = df_v[df_v['lojista'].isin(lista_oficial)].copy()
                df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
                if st.session_state.perfil == "admin":
                    st.title("👨‍✈️ Painel Geral MJ")
                    escolha = st.sidebar.multiselect("Lojistas:", options=lista_oficial, default=lista_oficial)
                    v_c = df_v[df_v['lojista'].isin(escolha)].copy()
                else:
                    st.title(f"🏠 Suas Vendas: {st.session_state.usuario}")
                    v_c = df_v[df_v['lojista'] == st.session_state.usuario].copy()

                if not v_c.empty:
                    st.sidebar.divider()
                    d_ini = st.sidebar.date_input("Início", v_c['data_dt'].min().date())
                    d_fim = st.sidebar.date_input("Fim", v_c['data_dt'].max().date())
                    v_c = v_c[(v_c['data_dt'].dt.date >= d_ini) & (v_c['data_dt'].dt.date <= d_fim)]
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}")
                    m2.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
                    m3.metric("Qtd Vendas", len(v_c))
                    if st.session_state.perfil == "admin": m4.metric("Seu Lucro (R$)", f"R$ {v_c['spread_rs'].sum():,.2f}")
                    st.write("---")
                    st.dataframe(v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
                else: st.info("Sem vendas para o filtro.")
            else: st.info("Sem dados.")
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções Comercial v20.0")
