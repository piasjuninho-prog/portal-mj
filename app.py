import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

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
    u = st.text_input("Usuário ou E-mail").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if (u == "admin" and p == "mj123") or (u == "admin@mjpag.com" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            try:
                res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
                if res.data and p == str(res.data[0].get('senha', '12345')):
                    st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
                else: st.error("❌ Credenciais inválidas.")
            except: st.warning("🔄 Conectando...")
else:
    # --- MENU LATERAL ---
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 🏫 ABA GESTÃO ---
    if menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        t1, t2 = st.tabs(["📋 Lista de Clientes", "➕ Novo Cadastro"])
        with t2:
            with st.form("cad_est", clear_on_submit=True):
                n = st.text_input("Nome Fantasia")
                e = st.text_input("E-mail de Login")
                d = st.text_input("CNPJ ou CPF")
                a = st.selectbox("Adquirente", ["InfinitePay", "PicPay", "Stone"])
                if st.form_submit_button("💾 Salvar Novo"):
                    if n and e:
                        conn.table("estabelecimentos").insert({"nome_fantasia": n.upper().strip(), "email": e.lower().strip(), "cnpj_cpf": d, "adquirente": a, "senha": "12345"}).execute()
                        st.success("✅ Cadastrado!"); st.rerun()
        with t1:
            res_e = conn.table("estabelecimentos").select("*").execute()
            if res_e.data:
                df_e = pd.DataFrame(res_e.data)
                st.data_editor(df_e, column_order=("nome_fantasia", "email", "senha", "adquirente", "nome_plano_ativo"), use_container_width=True, hide_index=True)

    # --- 📂 ABA PLANOS ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        t_v, t_n = st.tabs(["📋 Meus Planos", "➕ Criar Novo"])
        with t_v:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                p_s = st.selectbox("Escolha o Plano:", [p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == p_s)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_piv = pd.pivot_table(pd.DataFrame(res_t.data), values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)
        with t_n:
            nome_p = st.text_input("Nome do Plano")
            band_s = st.selectbox("Configurar Bandeira:", ORDEM_BANDEIRAS)
            df_ed = st.data_editor(pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo (%)": [0.0]*13}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira"):
                res = conn.table("planos_mj").select("*").eq("nome_plano", nome_p.upper().strip()).execute()
                if not res.data: res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper().strip()}).execute()
                id_p = res.data[0]['id']
                batch = [{"id_plano": id_p, "bandeira": band_s, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo (%)']/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Taxas Salvas!"); st.rerun()

    # --- 👤 ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina ao Cliente")
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        if res_e.data and res_p.data:
            with st.form("vinculo_ns"):
                c_sel = st.selectbox("Selecione o Cliente", [e['nome_fantasia'] for e in res_e.data])
                ns_input = st.text_input("Número de Série (NS)")
                p_sel = st.selectbox("Selecione o Plano", [p['nome_plano'] for p in res_p.data])
                if st.form_submit_button("✅ Finalizar Vínculo"):
                    if ns_input:
                        try:
                            # Tenta salvar o vínculo
                            conn.table("maquinas_ns").upsert({
                                "ns": ns_input.strip(), 
                                "nome_lojista": c_sel, 
                                "nome_plano": p_sel
                            }).execute()
                            # Atualiza o plano ativo na ficha do cliente
                            conn.table("estabelecimentos").update({"nome_plano_ativo": p_sel}).eq("nome_fantasia", c_sel).execute()
                            st.success(f"✅ Máquina {ns_input} vinculada ao cliente {c_sel}!")
                        except Exception as e:
                            st.error(f"Erro ao salvar vínculo: {e}")
                    else: st.error("Digite o NS.")
        else: st.warning("Cadastre clientes e planos primeiro.")

    # --- 🏠 DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # Busca Tabelas
            df_v = pd.DataFrame(conn.table("vendas").select("*").execute().data)
            df_m = pd.DataFrame(conn.table("maquinas_ns").select("*").execute().data)
            df_t = pd.DataFrame(conn.table("taxas_dos_planos").select("*").execute().data)
            df_p = pd.DataFrame(conn.table("planos_mj").select("id, nome_plano").execute().data)

            if not df_v.empty and not df_m.empty:
                # Merge: Venda + Máquina + Plano + Taxas
                df = pd.merge(df_v, df_m, on='ns', how='inner')
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df = pd.merge(df, df_t, left_on=['id_y', 'bandeira', 'plano'], right_on=['id_plano', 'bandeira', 'meio'], how='left')
                
                df['data_dt'] = df['data_venda'].apply(converter_data)
                df = df.dropna(subset=['data_dt'])
                
                if st.session_state.perfil == "admin":
                    lista = sorted(df['nome_lojista'].unique())
                    esc = st.sidebar.multiselect("Lojistas:", lista, default=lista)
                    df = df[df['nome_lojista'].isin(esc)]
                else: df = df[df['nome_lojista'] == st.session_state.usuario]

                if not df.empty:
                    # Métricas
                    df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                    df['liq'] = df['bruto'] * (1 - df['t_cli'])
                    
                    st.title("📊 Dashboard")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Bruto Total", f"R$ {df['bruto'].sum():,.2f}")
                    c2.metric("Líquido Total", f"R$ {df['liq'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto', 'liq']].sort_index(ascending=False), use_container_width=True)
                else: st.warning("Sem dados vinculados.")
            else: st.info("Vincule as máquinas aos clientes na aba Vincular.")
        except Exception as e: st.error(f"Aguardando sincronização... ({e})")

st.sidebar.caption("MJ Soluções v55.0")
