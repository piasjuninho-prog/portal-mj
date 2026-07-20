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

def limpar_ns(val):
    return str(val).strip().upper().lstrip('0') if val else ""

# --- LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None
if st.session_state.perfil is None:
    st.title("🔐 Portal MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("Login inválido.")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Gestão", "👤 Vincular", "📂 Planos", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- ABA GESTÃO (COM CADASTRO NOVO) ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        
        # Formulário para Novo Cliente
        with st.expander("➕ CADASTRAR NOVO CLIENTE"):
            with st.form("form_novo_cliente"):
                novo_nome = st.text_input("Nome Fantasia")
                novo_email = st.text_input("Email de Login")
                nova_senha = st.text_input("Senha", value="12345")
                novo_adq = st.selectbox("Adquirente Padrão", ["PagBank", "PicPay", "InfinitePay"])
                
                if st.form_submit_button("💾 Salvar Estabelecimento"):
                    if novo_nome and novo_email:
                        conn.table("estabelecimentos").insert({
                            "nome_fantasia": novo_nome.upper().strip(),
                            "email": novo_email.lower().strip(),
                            "senha": nova_senha,
                            "adquirente": novo_adq
                        }).execute()
                        st.success(f"Estabelecimento {novo_nome} cadastrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Preencha Nome e Email!")

        st.write("---")
        st.write("### Estabelecimentos Ativos")
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data:
            st.data_editor(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina")
        res_e = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        lista_clientes = sorted([e['nome_fantasia'] for e in res_e.data]) if res_e.data else []
        lista_planos = sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else ["PADRAO"]
        with st.form("form_vinculo"):
            cliente_sel = st.selectbox("Selecione o Cliente", lista_clientes)
            plano_sel = st.selectbox("Selecione o Plano de Taxas", lista_planos)
            ns_input = st.text_area("Digite os NS (separados por vírgula)")
            if st.form_submit_button("✅ Salvar Vínculo"):
                import re
                numeros = re.split(r'[,\n\s]+', ns_input)
                for n in numeros:
                    ns_limpo = limpar_ns(n)
                    if ns_limpo: conn.table("maquinas_ns").upsert({"ns": ns_limpo, "nome_lojista": cliente_sel, "nome_plano": plano_sel}).execute()
                st.success("Vinculado!"); st.rerun()

    # --- ABA DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="ref")
        st.title("📊 Dashboard")
        d_sel = st.sidebar.date_input("Data", date(2026, 7, 18))

        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data and m_res.data:
            df_v, df_m = pd.DataFrame(v_res.data), pd.DataFrame(m_res.data)
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id': 'id_p'})

            df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt'].dt.date == d_sel]
            df_v['link'], df_m['link'] = df_v['ns'].apply(limpar_ns), df_m['ns'].apply(limpar_ns)

            # Diagnóstico de Órfãs
            df_orfas = df_v[~df_v['link'].isin(df_m['link'])].copy()
            if not df_orfas.empty:
                st.warning(f"⚠️ Existem {len(df_orfas)} vendas sem vínculo para este dia (Total: R$ {pd.to_numeric(df_orfas['bruto']).sum():,.2f})")
                st.write("Abaixo estão os NS que você precisa copiar e vincular:")
                st.table(df_orfas[['bruto', 'ns', 'adquirente']])

            df = pd.merge(df_v, df_m, on='link', how='inner')
            if not df.empty:
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df['pl_adj'] = df['plano'].astype(str).str.lower().replace('crédito', 'à vista')
                df_t_c = df_t.drop_duplicates(subset=['id_plano', 'bandeira', 'meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
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

st.sidebar.caption("MJ Soluções v167.0")
