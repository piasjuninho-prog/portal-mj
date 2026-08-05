import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- MEMÓRIA ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'usuario' not in st.session_state: st.session_state.usuario = ""
if 'perfil' not in st.session_state: st.session_state.perfil = None

# --- CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# --- CONSTANTES ---
MODALIDADES_ORDEM = ["pix", "débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard", "pix"]

def limpar_ns(val): 
    return str(val).strip().upper().lstrip('0') if val else ""

# --- LOGIN ---
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
            else: st.error("❌ Login ou senha incorretos.")
else:
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    res_est = conn.table("estabelecimentos").select("nome_fantasia").execute()
    todos_lojistas = sorted([e['nome_fantasia'] for e in res_est.data]) if res_est.data else []

    if st.session_state.perfil == "admin":
        st.sidebar.subheader("Filtros")
        esc_lojistas = st.sidebar.multiselect("Filtrar Lojistas:", todos_lojistas, default=todos_lojistas)
        d_sel = st.sidebar.date_input("Data do Filtro", date.today())
        st.sidebar.divider()
        menu = st.sidebar.radio("GERENCIAMENTO", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    else:
        esc_lojistas = [st.session_state.usuario]
        d_sel = st.sidebar.date_input("Data do Filtro", date.today())
        menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "🚪 Sair"])
    
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- ABA GESTÃO ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão")
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- ABA PLANOS (v201.0 - EDIÇÃO INTELIGENTE) ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        tab_v, tab_e = st.tabs(["📋 Visualizar Planos", "⚙️ Criar ou Editar"])
        res_p = conn.table("planos_mj").select("*").execute()
        lista_planos = sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else []

        with tab_v:
            if lista_planos:
                ps = st.selectbox("Plano para Ver:", lista_planos)
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_t = pd.DataFrame(res_t.data)
                    df_t['Taxa Venda (%)'] = df_t['taxa_decimal'].apply(lambda x: f"{x*100:.2f}%")
                    df_grid = pd.pivot_table(df_t, values='Taxa Venda (%)', index='meio', columns='bandeira', aggfunc='first').reindex(index=MODALIDADES_ORDEM, columns=ORDEM_BANDEIRAS)
                    st.write("### Grade de Taxas (O que o cliente paga)")
                    st.dataframe(df_grid.fillna("-"), use_container_width=True)

        with tab_e:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                modo = st.radio("Ação:", ["Criar Novo Plano", "Editar Existente"], horizontal=True)
                nome_f = st.selectbox("Escolha o Plano:", lista_planos) if modo == "Editar Existente" else st.text_input("Nome do Novo Plano")
                band_sel = st.selectbox("Selecione a Bandeira:", ORDEM_BANDEIRAS)
                
                # --- LÓGICA DE CARREGAMENTO AUTOMÁTICO ---
                df_base = pd.DataFrame({
                    "Modalidade": ["pix"] if band_sel == "pix" else MODALIDADES_ORDEM, 
                    "Taxa Venda (%)": 0.0, 
                    "Taxa Custo (%)": 0.0
                })
                
                if modo == "Editar Existente" and nome_f:
                    id_edit = next(p['id'] for p in res_p.data if p['nome_plano'] == nome_f)
                    db_taxas = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_edit).eq("bandeira", band_sel).execute()
                    if db_taxas.data:
                        for item in db_taxas.data:
                            idx = df_base.index[df_base['Modalidade'] == item['meio']]
                            if not idx.empty:
                                df_base.at[idx[0], "Taxa Venda (%)"] = float(item['taxa_decimal']) * 100
                                df_base.at[idx[0], "Taxa Custo (%)"] = float(item['custo_decimal']) * 100

                st.write(f"Editando taxas de: **{band_sel.upper()}**")
                df_ed = st.data_editor(df_base, use_container_width=True, hide_index=True, key=f"editor_{nome_f}_{band_sel}")

                if st.button("💾 Salvar Bandeira"):
                    if nome_f:
                        p_res = conn.table("planos_mj").upsert({"nome_plano": str(nome_f).upper().strip()}, on_conflict="nome_plano").execute()
                        id_p_f = p_res.data[0]['id']
                        conn.table("taxas_dos_planos").delete().eq("id_plano", id_p_f).eq("bandeira", band_sel).execute()
                        batch = [{"id_plano": id_p_f, "bandeira": band_sel, "meio": r['Modalidade'], "taxa_decimal": float(r['Taxa Venda (%)'])/100, "custo_decimal": float(r['Taxa Custo (%)'])/100} for _, r in df_ed.iterrows()]
                        conn.table("taxas_dos_planos").insert(batch).execute()
                        st.success("✅ Atualizado!"); st.rerun()
            with col_b:
                st.subheader("🗑️ Apagar")
                if lista_planos:
                    pl_del = st.selectbox("Plano para apagar:", lista_planos, key="del_p")
                    if st.button("🔥 APAGAR TUDO"):
                        id_d = next(p['id'] for p in res_p.data if p['nome_plano'] == pl_del)
                        conn.table("taxas_dos_planos").delete().eq("id_plano", id_d).execute()
                        conn.table("planos_mj").delete().eq("id", id_d).execute()
                        st.rerun()

    # --- ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina")
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vinc"):
            c = st.selectbox("Cliente", todos_lojistas)
            ns_txt = st.text_area("NS")
            pl = st.selectbox("Plano", sorted([p['nome_plano'] for p in res_p.data]))
            if st.form_submit_button("✅ Vincular"):
                import re
                for n in re.split(r'[,\n\s]+', ns_txt):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar_ns(n), "nome_lojista": c, "nome_plano": pl}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute()
                st.success("OK!"); st.rerun()

    # --- ABA DASHBOARD ---
    elif menu == "🏠 Dashboard":
        st_autorefresh(interval=60000, key="refresh_dash")
        st.title("📊 Dashboard Financeiro")
        v_res, m_res = conn.table("vendas").select("*").execute(), conn.table("maquinas_ns").select("*").execute()
        t_res, p_res = conn.table("taxas_dos_planos").select("*").execute(), conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data and m_res.data:
            df_v, df_m = pd.DataFrame(v_res.data), pd.DataFrame(m_res.data)
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})
            df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt'].dt.date == d_sel]
            df_v['link'], df_m['link'] = df_v['ns'].apply(limpar_ns), df_m['ns'].apply(limpar_ns)
            df = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='inner', suffixes=('', '_m'))
            df = df[df['nome_lojista'].isin(esc_lojistas)]

            if not df.empty:
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                df['pl_adj'] = df['plano'].astype(str).str.lower().replace('crédito','à vista').apply(lambda x: x + "x" if "em " in x and not x.endswith("x") else x)
                df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                df['t_cus'] = pd.to_numeric(df.get('custo_decimal', 0), errors='coerce').fillna(0)
                df['liq_v'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                df['lucro_v'] = (df['bruto_v'] * (df['t_cli'] - df['t_cus'])).round(2)
                df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Bruto", f"R$ {df['bruto_v'].sum():,.2f}"); c2.metric("Líquido", f"R$ {df['liq_v'].sum():,.2f}")
                c3.metric("Vendas", len(df)); c4.metric("Lucro MJ", f"R$ {df['lucro_v'].sum():,.2f}")
                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)
st.sidebar.caption("MJ Soluções v201.0")
