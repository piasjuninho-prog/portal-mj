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
    st.title("🔐 Portal MJ PAG - Login")
    u = st.text_input("E-mail de Acesso ou Usuário").lower().strip() 
    p = st.text_input("Senha", type="password")
    
    if st.button("Entrar no Sistema", use_container_width=True):
        if (u == "admin" and p == "mj123") or (u == "admin@mjpag.com" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            try:
                # Busca o usuário pelo e-mail
                res_user = conn.table("estabelecimentos").select("*").eq("email", u).execute()
                if res_user.data:
                    dados_user = res_user.data[0]
                    # Comparação de senha
                    if str(p) == str(dados_user.get('senha', '12345')):
                        st.session_state.perfil = "cliente"
                        st.session_state.usuario = dados_user['nome_fantasia']
                        st.rerun()
                    else:
                        st.error("❌ Senha incorreta. Tente novamente.")
                else:
                    st.error("❌ E-mail não encontrado no cadastro.")
            except Exception as e:
                # Caso a conexão com o banco falhe na primeira tentativa
                st.warning("🔄 Estabelecendo conexão... Por favor, clique em Entrar novamente.")
else:
    # --- 3. MENU LATERAL ---
    opcoes_menu = ["🏠 Dashboard", "🏫 Estabelecimentos", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"] if st.session_state.perfil == "admin" else ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    st.sidebar.markdown(f"""<div style="background:#f0f2f6;padding:10px;border-radius:5px;border-left:5px solid #2ecc71;">
        <small>🔄 <b>Sincronizado:</b> {datetime.now().strftime('%H:%M:%S')}</small></div>""", unsafe_allow_html=True)
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes_menu)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 4. ABA: ESTABELECIMENTOS (ADMIN) ---
    if menu == "🏫 Estabelecimentos" and st.session_state.perfil == "admin":
        st.title("🏫 Gestão de Estabelecimentos")
        tab_list, tab_cad = st.tabs(["📋 Lista de Clientes", "➕ Novo Cadastro"])
        with tab_cad:
            with st.form("cad_estabelecimento", clear_on_submit=True):
                nome_f = st.text_input("Nome Fantasia")
                email_cli = st.text_input("E-mail de Login")
                doc = st.text_input("CNPJ ou CPF")
                adq = st.selectbox("Adquirente", ["InfinitePay", "PicPay", "Stone", "PagSeguro"])
                prov = st.text_input("Provedor", value="MJ PAG")
                if st.form_submit_button("💾 Salvar Novo"):
                    conn.table("estabelecimentos").insert({"nome_fantasia": nome_f.upper().strip(), "email": email_cli.lower().strip(), "cnpj_cpf": doc, "adquirente": adq, "provedor": prov.upper(), "senha": "12345"}).execute()
                    st.success("Cadastrado!"); st.rerun()
        with tab_list:
            res_est = conn.table("estabelecimentos").select("*").execute()
            if res_est.data:
                df_est = pd.DataFrame(res_est.data)
                df_ed = st.data_editor(df_est, column_order=("nome_fantasia", "email", "senha", "adquirente", "provedor", "nome_plano_ativo"), column_config={"id": None, "nome_plano_ativo": st.column_config.TextColumn("Plano", disabled=True)}, use_container_width=True, hide_index=True)
                if st.button("💾 Salvar Alterações"):
                    for i, r in df_ed.iterrows():
                        conn.table("estabelecimentos").update({"nome_fantasia": str(r.get("nome_fantasia")).upper(), "email": str(r.get("email")).lower(), "senha": str(r.get("senha")), "adquirente": r.get("adquirente"), "provedor": r.get("provedor")}).eq("id", r["id"]).execute()
                    st.success("✅ Atualizado!"); st.rerun()

    # --- 5. ABA: CRIAR PLANOS (ADMIN) ---
    elif menu == "📂 Criar Planos" and st.session_state.perfil == "admin":
        st.title("📂 Planos de Taxas")
        tab_view, tab_new = st.tabs(["📋 Meus Planos", "➕ Criar Novo"])
        with tab_view:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                p_sel = st.selectbox("Escolha o Plano:", options=[p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_sel)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_piv = pd.DataFrame(res_t.data).pivot(index='meio', columns='bandeira', values='taxa_decimal').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
        with tab_new:
            nome_p = st.text_input("Nome do Plano")
            df_setup = pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Mastercard (%)": [0.0]*13, "Visa (%)": [0.0]*13, "Elo (%)": [0.0]*13, "Amex (%)": [0.0]*13, "Hipercard (%)": [0.0]*13})
            df_ed_p = st.data_editor(df_setup, use_container_width=True, hide_index=True)
            if st.button("🚀 SALVAR PLANO"):
                res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper()}).execute()
                id_p = res.data[0]['id']
                batch = []
                b_map = {"Mastercard (%)": "mastercard", "Visa (%)": "visa", "Elo (%)": "elo", "Amex (%)": "amex", "Hipercard (%)": "hipercard"}
                for _, row in df_ed_p.iterrows():
                    for col, band in b_map.items(): batch.append({"id_plano": id_p, "bandeira": band, "meio": row['Modalidade'], "taxa_decimal": row[col]/100})
                conn.table("taxas_dos_planos").insert(batch).execute()
                st.success("Salvo!"); st.rerun()

    # --- 6. ABA: VINCULAR CLIENTE (ADMIN) ---
    elif menu == "👤 Vincular Cliente" and st.session_state.perfil == "admin":
        st.title("👤 Vincular Plano")
        res_p = conn.table("planos_mj").select("id, nome_plano").execute()
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        if res_p.data and res_e.data:
            d_p = {p['nome_plano']: p['id'] for p in res_p.data}
            l_c = sorted([e['nome_fantasia'] for e in res_e.data])
            with st.form("vinculo"):
                c_sel = st.selectbox("Estabelecimento", l_c); ns_in = st.text_input("NS (Separe por vírgula)"); p_sel = st.selectbox("Plano", list(d_p.keys()))
                if st.form_submit_button("✅ FINALIZAR"):
                    res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", d_p[p_sel]).execute()
                    novas = []
                    for ns in [n.strip() for n in ns_in.split(",")]:
                        for t in res_t.data: novas.append({"cliente": c_sel, "ns": ns, "bandeira": t['bandeira'], "meio": t['meio'], "taxa_decimal": t['taxa_decimal']})
                    conn.table("taxas_clientes").insert(novas).execute()
                    conn.table("estabelecimentos").update({"nome_plano_ativo": p_sel}).eq("nome_fantasia", c_sel).execute()
                    st.success("Vínculo OK!")

    # --- 7. ABA: DASHBOARD ---
    elif menu in ["🏠 Dashboard"]:
        st_autorefresh(interval=30000, key="refresh")
        try:
            res_of = conn.table("estabelecimentos").select("nome_fantasia").execute()
            list_of = [e['nome_fantasia'] for e in res_of.data]
            df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            if not df_v.empty:
                df_v = df_v[df_v['lojista'].isin(list_of)].copy()
                df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
                if st.session_state.perfil == "admin":
                    st.title("👨‍✈️ Painel Geral MJ")
                    escolha = st.sidebar.multiselect("Lojistas:", options=list_of, default=list_of)
                    v_c = df_v[df_v['lojista'].isin(escolha)].copy()
                else:
                    st.title(f"🏠 Suas Vendas: {st.session_state.usuario}"); v_c = df_v[df_v['lojista'] == st.session_state.usuario].copy()
                if not v_c.empty:
                    st.sidebar.divider()
                    d_ini = st.sidebar.date_input("Início", v_c['data_dt'].min().date()); d_fim = st.sidebar.date_input("Fim", v_c['data_dt'].max().date()); v_c = v_c[(v_c['data_dt'].dt.date >= d_ini) & (v_c['data_dt'].dt.date <= d_fim)]
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}"); m2.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}"); m3.metric("Qtd Vendas", len(v_c))
                    if st.session_state.perfil == "admin": m4.metric("Seu Lucro (R$)", f"R$ {v_c['spread_rs'].sum():,.2f}")
                    st.write("---"); st.dataframe(v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].sort_index(ascending=False), use_container_width=True)
            else: st.info("Sem dados sincronizados.")
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções Comercial v25.0")
