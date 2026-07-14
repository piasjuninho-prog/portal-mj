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

# Constantes
ORDEM_MODALIDADES = ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard"]

def limpar(val): return str(val).strip().upper().lstrip('0') if val else ""

# --- LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 Login MJ PAG PRO")
    u, p = st.text_input("Usuário").lower(), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "mj123": st.session_state.auth = True; st.rerun()
        else: st.error("Acesso Negado")
else:
    menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "🏫 Gestão", "📂 Planos", "👤 Vincular", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- ABA GESTÃO ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão de Clientes")
        with st.expander("➕ CADASTRAR NOVO CLIENTE"):
            with st.form("novo_c"):
                n, e = st.text_input("Nome Fantasia"), st.text_input("Email")
                if st.form_submit_button("Salvar"):
                    conn.table("estabelecimentos").insert({"nome_fantasia": n.upper(), "email": e.lower(), "senha": "12345"}).execute()
                    st.success("Cadastrado!"); st.rerun()
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)

    # --- ABA PLANOS (VERSÃO v157.0 - FIX VALUEERROR) ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        t1, t2 = st.tabs(["📋 Visualizar Planos", "➕ Criar/Editar Plano"])
        
        with t1:
            res_p = conn.table("planos_mj").select("*").execute()
            if res_p.data:
                ps = st.selectbox("Selecione o Plano:", [p['nome_plano'] for p in res_p.data])
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_t = pd.DataFrame(res_t.data)
                    df_piv = pd.pivot_table(df_t, values='taxa_decimal', index='meio', columns='bandeira', aggfunc='last').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS)
                    st.dataframe(df_piv.map(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "-"), use_container_width=True)

        with t2:
            st.subheader("Configurar Taxas")
            nome_p_input = st.text_input("Nome do Plano (Ex: RAFHI IPHONE)")
            band_sel = st.selectbox("Selecione a Bandeira:", ORDEM_BANDEIRAS)
            
            df_ed = st.data_editor(pd.DataFrame({
                "Modalidade": ORDEM_MODALIDADES, 
                "Taxa Cliente (%)": [0.0]*13, 
                "Custo (%)": [0.0]*13
            }), use_container_width=True, hide_index=True)
            
            if st.button("💾 Salvar Bandeira no Plano"):
                if not nome_p_input:
                    st.error("Digite o nome do plano primeiro!")
                else:
                    # 1. Garante que o plano existe e pega o ID
                    p_res = conn.table("planos_mj").upsert({"nome_plano": nome_p_input.upper().strip()}, on_conflict="nome_plano").execute()
                    id_p = p_res.data[0]['id']
                    
                    # 2. Deleta taxas antigas para não dar erro de duplicidade
                    conn.table("taxas_dos_planos").delete().eq("id_plano", id_p).eq("bandeira", band_sel).execute()
                    
                    # 3. Monta o lote de dados tratando valores vazios (None)
                    batch = []
                    for _, r in df_ed.iterrows():
                        # Converte para float tratando vazios como 0.0
                        t_cli = float(r['Taxa Cliente (%)']) if pd.notnull(r['Taxa Cliente (%)']) else 0.0
                        t_cus = float(r['Custo (%)']) if pd.notnull(r['Custo (%)']) else 0.0
                        
                        batch.append({
                            "id_plano": id_p,
                            "bandeira": band_sel,
                            "meio": r['Modalidade'],
                            "taxa_decimal": t_cli / 100,
                            "custo_decimal": t_cus / 100
                        })
                    
                    # 4. Insere no banco
                    conn.table("taxas_dos_planos").insert(batch).execute()
                    st.success(f"✅ Taxas de {band_sel.upper()} salvas no plano {nome_p_input}!")
                    st.balloons()

    # --- ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquinas")
        res_e, res_p = conn.table("estabelecimentos").select("nome_fantasia").execute(), conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vinc"):
            c = st.selectbox("Cliente", [e['nome_fantasia'] for e in res_e.data])
            ns_txt = st.text_area("NS (Números de Série - um por linha ou vírgula)")
            plano = st.selectbox("Plano", [p['nome_plano'] for p in res_p.data])
            if st.form_submit_button("Vincular Agora"):
                import re
                for n in re.split(r'[,\n\r]+', ns_txt):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar(n), "nome_lojista": c, "nome_plano": plano}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": plano}).eq("nome_fantasia", c).execute()
                st.success("✅ Vínculos realizados!")

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
            df_v['link'], df_m['link'] = df_v['ns'].apply(limpar), df_m['ns'].apply(limpar)
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
                c1.metric("Bruto", f"R$ {df['bruto_v'].sum():,.2f}"); c2.metric("Líquido", f"R$ {df['liq'].sum():,.2f}"); c3.metric("Vendas", len(df))
                st.dataframe(df[['data_venda', 'nome_lojista', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq']], use_container_width=True)
