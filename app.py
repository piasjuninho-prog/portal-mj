import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

def limpar(val): return str(val).strip().upper().lstrip('0') if val else ""

# --- LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 Login MJ PAG PRO")
    u, p = st.text_input("Usuário").lower(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123": st.session_state.auth = True; st.rerun()
        else: st.error("Acesso Negado")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Gestão", "👤 Vincular", "🚪 Sair"])
    
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- ABA GESTÃO (PARA CADASTRAR NOVOS CLIENTES) ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão de Clientes")
        
        with st.expander("➕ CADASTRAR NOVO CLIENTE"):
            with st.form("novo_cliente"):
                nome = st.text_input("Nome Fantasia (Ex: LOJA DO JOAO)")
                email = st.text_input("Email de Login")
                senha = st.text_input("Senha", value="12345")
                adq = st.selectbox("Adquirente Padrão", ["PagBank", "PicPay", "InfinitePay"])
                if st.form_submit_button("Salvar Cliente"):
                    if nome and email:
                        conn.table("estabelecimentos").insert({
                            "nome_fantasia": nome.upper().strip(),
                            "email": email.lower().strip(),
                            "senha": senha,
                            "adquirente": adq
                        }).execute()
                        st.success(f"Cliente {nome} cadastrado!")
                        st.rerun()

        st.write("### Clientes Cadastrados")
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)

    # --- ABA VINCULAR (PARA LIGAR NS AO CLIENTE) ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquinas")
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        
        if not res_e.data:
            st.error("Cadastre um cliente primeiro na aba Gestão!")
        else:
            with st.form("vinc"):
                cliente = st.selectbox("Selecione o Cliente", [e['nome_fantasia'] for e in res_e.data])
                ns_lista = st.text_area("Números de Série (NS) - um por linha ou separados por vírgula")
                plano = st.selectbox("Selecione o Plano de Taxas", [p['nome_plano'] for p in res_p.data] if res_p.data else ["PADRAO"])
                
                if st.form_submit_button("Vincular Agora"):
                    import re
                    # Limpa e separa os NS
                    numeros = re.split(r'[,\n\r]+', ns_lista)
                    for n in numeros:
                        if n.strip():
                            conn.table("maquinas_ns").upsert({
                                "ns": limpar(n),
                                "nome_lojista": cliente,
                                "nome_plano": plano
                            }).execute()
                    # Atualiza o plano ativo na ficha do cliente
                    conn.table("estabelecimentos").update({"nome_plano_ativo": plano}).eq("nome_fantasia", cliente).execute()
                    st.success("Vínculos realizados com sucesso!")

    # --- ABA DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st.title("📊 Dashboard")
        d_sel = st.sidebar.date_input("Data", date(2026, 7, 13))
        
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data and m_res.data:
            df_v, df_m = pd.DataFrame(v_res.data), pd.DataFrame(m_res.data)
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})

            df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt'].dt.date == d_sel]
            df_v['link'] = df_v['ns'].apply(limpar)
            df_m['link'] = df_m['ns'].apply(limpar)
            
            # Alerta NS não vinculado
            faltando = set(df_v['link'].unique()) - set(df_m['link'].unique())
            if faltando: st.warning(f"⚠️ NS pendentes de vínculo: {', '.join(faltando)}")

            df = pd.merge(df_v, df_m, on='link', how='inner')
            if not df.empty:
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df['pl_adj'] = df['plano'].astype(str).str.lower().replace('crédito','à vista')
                df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')

                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                df['liq'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                c1, c2, c3 = st.columns(3)
                c1.metric("Bruto", f"R$ {df['bruto_v'].sum():,.2f}")
                c2.metric("Líquido", f"R$ {df['liq'].sum():,.2f}")
                c3.metric("Vendas", len(df))
                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq']], use_container_width=True)
            else: st.info("Nenhuma venda vinculada encontrada para este dia.")
