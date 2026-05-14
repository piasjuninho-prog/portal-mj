import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# Configuração visual
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
    st.title("🔐 Portal MJ PAG - Acesso")
    u = st.text_input("E-mail").lower().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if (u == "admin" and p == "mj123"):
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMIN"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Acesso negado.")
else:
    # --- MENU LATERAL ---
    opcoes = ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"]
    if st.session_state.perfil != "admin": opcoes = ["🏠 Dashboard", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 4. ABA GESTÃO (MANTIDA v52.0) ---
    if menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        t1, t2 = st.tabs(["📋 Lista", "➕ Novo Cadastro"])
        with t2:
            with st.form("cad_est"):
                n = st.text_input("Nome Fantasia"); e = st.text_input("E-mail"); a = st.selectbox("Adquirente", ["InfinitePay", "PicPay", "Stone"])
                if st.form_submit_button("Salvar"):
                    conn.table("estabelecimentos").insert({"nome_fantasia": n.upper(), "email": e.lower(), "adquirente": a, "senha": "12345"}).execute()
                    st.success("Cadastrado!"); st.rerun()
        with t1:
            res = conn.table("estabelecimentos").select("*").execute()
            if res.data: st.data_editor(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- 5. ABA PLANOS (MANTIDA v52.0) ---
    elif menu == "📂 Planos":
        st.title("📂 Configurar Planos")
        t_ver, t_criar = st.tabs(["📋 Meus Planos", "➕ Novo Plano"])
        with t_criar:
            nome_p = st.text_input("Nome do Plano (Ex: PLANO VIP)")
            band_s = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
            df_ed = st.data_editor(pd.DataFrame({"Modalidade": ORDEM_MODALIDADES, "Taxa Cliente (%)": [0.0]*13, "Custo (%)": [0.0]*13}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira"):
                res = conn.table("planos_mj").select("*").eq("nome_plano", nome_p.upper()).execute()
                if not res.data: res = conn.table("planos_mj").insert({"nome_plano": nome_p.upper()}).execute()
                id_p = res.data[0]['id']
                batch = [{"id_plano": id_p, "bandeira": band_s, "meio": r['Modalidade'], "taxa_decimal": r['Taxa Cliente (%)']/100, "custo_decimal": r['Custo (%)']/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Salvo!")

    # --- 6. ABA VINCULAR (AQUI VOCÊ ATRELA O NS AO CLIENTE) ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina ao Cliente")
        st.write("Aqui você atrela o código de série da máquina ao lojista e ao plano dele.")
        
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        
        if res_e.data and res_p.data:
            with st.form("vinculo_ns"):
                c_sel = st.selectbox("Selecione o Cliente", [e['nome_fantasia'] for e in res_e.data])
                ns_input = st.text_input("Número de Série da Máquina (NS)")
                plano_sel = st.selectbox("Selecione o Plano de Taxas", [p['nome_plano'] for p in res_p.data])
                
                if st.form_submit_button("✅ Finalizar Vínculo"):
                    if ns_input:
                        # Salva o vínculo NS -> Cliente -> Plano
                        conn.table("maquinas_ns").upsert({
                            "ns": ns_input.strip(),
                            "nome_lojista": c_sel,
                            "nome_plano": plano_sel
                        }).execute()
                        st.success(f"Máquina {ns_input} atrelada ao cliente {c_sel} no {plano_sel}!")
                    else: st.error("Digite o NS da máquina.")
        else: st.warning("Cadastre clientes e planos primeiro.")

    # --- 7. DASHBOARD (O CÉREBRO QUE JUNTA TUDO) ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=30000, key="refresh")
        try:
            # 1. Puxa as tabelas brutas
            df_vendas = pd.DataFrame(conn.table("vendas").select("*").execute().data)
            df_maquinas = pd.DataFrame(conn.table("maquinas_ns").select("*").execute().data)
            df_taxas = pd.DataFrame(conn.table("taxas_dos_planos").select("*").execute().data)
            df_planos_mj = pd.DataFrame(conn.table("planos_mj").select("id, nome_plano").execute().data)

            if not df_vendas.empty and not df_maquinas.empty:
                # 2. Casamento: Venda + Dono da Máquina (via NS)
                df = pd.merge(df_vendas, df_maquinas, on='ns', how='inner')
                
                # 3. Casamento: Dono da Máquina + ID do Plano
                df = pd.merge(df, df_planos_mj, left_on='nome_plano', right_on='nome_plano', how='left')

                # 4. Casamento: Venda + Taxas do Plano correspondente
                df = pd.merge(
                    df, df_taxas, 
                    left_on=['id_right', 'bandeira', 'plano'], 
                    right_on=['id_plano', 'bandeira', 'meio'], 
                    how='left'
                )

                df['data_dt'] = df['data_venda'].apply(converter_data)
                df = df.dropna(subset=['data_dt'])

                # Filtro de Perfil
                if st.session_state.perfil == "admin":
                    lista_lj = sorted(df['nome_lojista'].unique())
                    esc = st.sidebar.multiselect("Lojistas:", lista_lj, default=lista_lj)
                    df = df[df['nome_lojista'].isin(esc)]
                else:
                    df = df[df['nome_lojista'] == st.session_state.usuario]

                if not df.empty:
                    # Cálculos
                    df['bruto'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0.0)
                    df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0.0)
                    df['t_cus'] = pd.to_numeric(df.get('custo_decimal', 0.0), errors='coerce').fillna(0.0)
                    
                    df['liquido_total'] = df['bruto'] * (1 - df['t_cli'])
                    df['lucro_total'] = df['bruto'] * (df['t_cli'] - df['t_cus'])

                    st.title(f"📊 Dashboard Geral MJ")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Faturamento Bruto", f"R$ {df['bruto'].sum():,.2f}")
                    c2.metric("Líquido Esperado", f"R$ {df['liquido_total'].sum():,.2f}")
                    c3.metric("Vendas", len(df))
                    if st.session_state.perfil == "admin": 
                        c4.metric("Seu Lucro Real", f"R$ {df['lucro_total'].sum():,.2f}")

                    st.divider()
                    st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto', 'taxa_decimal', 'liquido_total']].sort_index(ascending=False), use_container_width=True)
                else: st.warning("Nenhum dado vinculado para o filtro.")
            else: st.info("Vá em 'Vincular' para atrelar as máquinas aos clientes.")
        except Exception as e: st.error(f"Erro: {e}")

st.sidebar.caption("MJ Soluções v53.0")
