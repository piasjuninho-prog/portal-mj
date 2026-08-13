import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
import re

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO COM BANCO DE DADOS ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# --- CONSTANTES ---
ORDEM_MODALIDADES = ["pix", "débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
ORDEM_BANDEIRAS = ["mastercard", "visa", "elo", "amex", "hipercard", "pix", "picpay"]

def limpar_ns(val):
    """Limpa NS removendo zeros à esquerda e caracteres especiais para garantir o vínculo"""
    if not val: return ""
    # Remove tudo que não é letra ou número, converte pra maiúsculo e remove zeros à esquerda
    res = re.sub(r'[^A-Z0-9]', '', str(val).strip().upper()).lstrip('0')
    return res if res else "0"

# --- CONTROLE DE ACESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'usuario' not in st.session_state: st.session_state.usuario = ""
if 'perfil' not in st.session_state: st.session_state.perfil = None

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
            else: st.error("❌ Credenciais inválidas.")
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    res_est = conn.table("estabelecimentos").select("nome_fantasia").execute()
    todos_lojistas = sorted([e['nome_fantasia'] for e in res_est.data]) if res_est.data else []

    if st.session_state.perfil == "admin":
        st.sidebar.subheader("Filtros Dashboard")
        # Inclusão da categoria de não vinculados para o Admin não perder vendas
        esc_lojistas = st.sidebar.multiselect("Filtrar Lojistas:", ["⚠️ NÃO VINCULADO"] + todos_lojistas, default=["⚠️ NÃO VINCULADO"] + todos_lojistas)
        d_sel = st.sidebar.date_input("Data do Filtro", date.today())
        st.sidebar.divider()
        menu = st.sidebar.radio("NAVEGAÇÃO", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    else:
        esc_lojistas = [st.session_state.usuario]
        d_sel = st.sidebar.date_input("Data do Filtro", date.today())
        menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "🚪 Sair"])
    
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- ABA GESTÃO ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        c1, c2 = st.columns(2)
        with c1:
            with st.expander("➕ CADASTRAR NOVO"):
                with st.form("add"):
                    n, e = st.text_input("Nome Fantasia"), st.text_input("Email")
                    if st.form_submit_button("Salvar"):
                        conn.table("estabelecimentos").insert({"nome_fantasia": n.upper().strip(), "email": e.lower().strip(), "senha": "12345"}).execute()
                        st.success("✅ Cadastrado!"); st.rerun()
        with c2:
            with st.expander("🗑️ EXCLUIR"):
                if todos_lojistas:
                    rem = st.selectbox("Remover:", todos_lojistas)
                    if st.button("Confirmar Exclusão"):
                        conn.table("estabelecimentos").delete().eq("nome_fantasia", rem).execute()
                        st.rerun()
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- ABA PLANOS ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        t1, t2 = st.tabs(["📋 Visualizar", "⚙️ Criar/Editar"])
        res_p = conn.table("planos_mj").select("*").execute()
        lista_p = sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else []
        with t1:
            if lista_p:
                ps = st.selectbox("Ver Plano:", lista_p)
                id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_v = pd.DataFrame(res_t.data)
                    df_v['%'] = df_v['taxa_decimal'].apply(lambda x: f"{x*100:.2f}%")
                    st.dataframe(pd.pivot_table(df_v, values='%', index='meio', columns='bandeira', aggfunc='first').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS).fillna("-"), use_container_width=True)
        with t2:
            modo = st.radio("Ação:", ["Novo", "Editar"], horizontal=True)
            nome_f = st.selectbox("Plano:", lista_p) if modo == "Editar" else st.text_input("Nome")
            band_s = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
            mods = ["pix"] if band_s == "pix" else [m for m in ORDEM_MODALIDADES if m != "pix"]
            df_ed = st.data_editor(pd.DataFrame({"Meio": mods, "Venda (%)": 0.0, "Custo (%)": 0.0}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira"):
                p_res = conn.table("planos_mj").upsert({"nome_plano": nome_f.upper().strip()}, on_conflict="nome_plano").execute()
                id_f = p_res.data[0]['id']
                conn.table("taxas_dos_planos").delete().eq("id_plano", id_f).eq("bandeira", band_s).execute()
                batch = [{"id_plano": id_f, "bandeira": band_s, "meio": r['Meio'], "taxa_decimal": float(r['Venda (%)'])/100, "custo_decimal": float(r['Custo (%)'])/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute()
                st.success("✅ Salvo!"); st.rerun()

    # --- ABA VINCULAR ---
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina/Terminal")
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vinc"):
            c = st.selectbox("Cliente", todos_lojistas)
            ns_txt = st.text_area("Números de Série / IDs Terminal (separe por vírgula)")
            pl = st.selectbox("Plano", sorted([p['nome_plano'] for p in res_p.data]))
            if st.form_submit_button("Salvar Vínculo"):
                for n in ns_txt.split(","):
                    if n.strip(): 
                        ns_limpo = limpar_ns(n)
                        conn.table("maquinas_ns").upsert({"ns": ns_limpo, "nome_lojista": c, "nome_plano": pl}).execute()
                conn.table("estabelecimentos").update({"nome_plano_ativo": pl}).eq("nome_fantasia", c).execute()
                st.success("✅ Vinculado!")

    # --- ABA DASHBOARD (VERSÃO REPARADA v212.0) ---
    elif menu == "🏠 Dashboard":
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=60000, key="refresh_v212")
        st.title("📊 Dashboard Financeiro")
        
        # 1. Coleta de Dados
        v_res = conn.table("vendas").select("*").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})
            
            # --- TRATAMENTO DE DATA ---
            df_v['dt'] = pd.to_datetime(df_v['data_venda'], dayfirst=True, errors='coerce')
            df_v = df_v[df_v['dt'].dt.date == d_sel].copy()
            
            # --- TRATAMENTO DE NS (Vínculo) ---
            df_v['link'] = df_v['ns'].apply(limpar_ns)
            df_m['link'] = df_m['ns'].apply(limpar_ns)
            
            # MUDANÇA PARA LEFT JOIN: Não apaga vendas sem dono
            df = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='left')
            df['nome_lojista'] = df['nome_lojista'].fillna("⚠️ NÃO VINCULADO")
            df['nome_plano'] = df['nome_plano'].fillna("SEM PLANO")

            # Status de recebimento do Robô
            bruto_total_dia = pd.to_numeric(df['bruto'], errors='coerce').sum()
            st.info(f"🏦 O banco possui **{len(df)}** vendas para este dia, totalizando **R$ {bruto_total_dia:,.2f}** bruto.")

            # Aplicar filtro de lojistas da sidebar
            df = df[df['nome_lojista'].isin(esc_lojistas)]

            if not df.empty:
                # Cruzamento com Planos e Taxas
                df = pd.merge(df, df_p, on='nome_plano', how='left')
                
                # Normalização de Plano (PicPay envia nomes variados)
                def normalizar_meio(row):
                    p = str(row['plano']).lower()
                    if 'débito' in p: return 'débito'
                    if 'pix' in p or str(row['bandeira']).lower() == 'pix': return 'pix'
                    # Procura número de parcelas (ex: "3x", "4 parcelas")
                    num = re.findall(r'\d+', p)
                    if num: return f"em {num[0]}x"
                    return 'à vista'
                
                df['pl_adj'] = df.apply(normalizar_meio, axis=1)
                
                # Merge com a tabela de taxas
                df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df = pd.merge(df, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                
                # Cálculos Financeiros
                df['bruto_v'] = pd.to_numeric(df['bruto'], errors='coerce').fillna(0)
                df['t_cli'] = pd.to_numeric(df['taxa_decimal'], errors='coerce').fillna(0)
                df['t_cus'] = pd.to_numeric(df.get('custo_decimal', 0), errors='coerce').fillna(0)
                
                df['liq_v'] = (df['bruto_v'] * (1 - df['t_cli'])).round(2)
                df['lucro'] = (df['bruto_v'] * (df['t_cli'] - df['t_cus'])).round(2)
                df['taxa_txt'] = (df['t_cli'] * 100).map("{:.2f}%".format)

                # Cards de Resumo
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Bruto (Filtrado)", f"R$ {df['bruto_v'].sum():,.2f}")
                c2.metric("Líquido Total", f"R$ {df['liq_v'].sum():,.2f}")
                c3.metric("Qtd Vendas", len(df))
                if st.session_state.perfil == "admin":
                    c4.metric("Lucro MJ Estimado", f"R$ {df['lucro'].sum():,.2f}")
                
                st.divider()
                # Tabela de Resultados
                st.dataframe(df[['data_venda', 'nome_lojista', 'adquirente', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)
                
                # Alertas para o Usuário
                if "⚠️ NÃO VINCULADO" in df['nome_lojista'].values:
                    st.warning("🚨 Existem vendas sem dono. Verifique o NS/ID Terminal na aba Vincular.")
                
                vendas_sem_taxa = df[df['taxa_decimal'].isna()]
                if not vendas_sem_taxa.empty:
                    st.error(f"⚠️ {len(vendas_sem_taxa)} vendas estão com taxa 0% porque o Plano ou Bandeira não foi configurado corretamente.")
            else:
                st.warning("Nenhuma venda encontrada para os filtros atuais.")
        else:
            st.error("Aguardando o robô sincronizar as primeiras vendas...")

st.sidebar.caption("MJ Soluções v212.0")
