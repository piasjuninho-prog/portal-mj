import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
import re
import unicodedata
from fpdf import FPDF

# 1. CONFIGURAÇÃO INICIAL
st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO COM BANCO DE DADOS ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# --- FUNÇÕES AUXILIARES ---
def limpar_ns(val):
    if not val: return ""
    return re.sub(r'[^A-Z0-9]', '', str(val).strip().upper()).lstrip('0')

def safe_text(text):
    if text is None: return ""
    text = str(text)
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).encode('ascii', 'ignore').decode('ascii')

def gerar_pdf_v239(df, data_ref, bruto, liquido, qtd):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 18)
    pdf.cell(277, 10, safe_text("MJ SOLUCOES - RELATORIO DETALHADO"), 0, 1, 'C')
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(277, 10, safe_text(f" Bruto: RS {bruto:,.2f}  |  Liquido: RS {liquido:,.2f}  |  Vendas: {qtd}"), 1, 1, 'C', 1)
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 9); pdf.set_fill_color(200, 200, 200)
    cols = [("Data", 25), ("Lojista", 55), ("NS", 40), ("Band", 20), ("Plano", 52), ("Taxa %", 25), ("Bruto", 30), ("Liq", 30)]
    for c, w in cols: pdf.cell(w, 8, c, 1, 0, 'C', 1)
    pdf.ln()
    pdf.set_font("Helvetica", '', 8)
    for _, r in df.iterrows():
        pdf.cell(25, 7, safe_text(r['data_venda']), 1, 0, 'C')
        pdf.cell(55, 7, safe_text(str(r['nome_lojista'])[:25]), 1, 0, 'L')
        pdf.cell(40, 7, safe_text(r['ns']), 1, 0, 'C')
        pdf.cell(20, 7, safe_text(r['bandeira']), 1, 0, 'C')
        pdf.cell(52, 7, safe_text(r['plano']), 1, 0, 'C')
        pdf.cell(25, 7, safe_text(r['taxa_txt']), 1, 0, 'C')
        pdf.cell(30, 7, f"{r['bruto_v']:,.2f}", 1, 0, 'R')
        pdf.cell(30, 7, f"{r['liq_v']:,.2f}", 1, 1, 'R')
    return bytes(pdf.output())

# --- LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Login MJ PAG PRO")
    u, p = st.text_input("Usuário").lower().strip(), st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "admin" and p == "mj123": 
            st.session_state.auth = True; st.session_state.perfil = "admin"; st.session_state.usuario = "ADMIN"; st.rerun()
        else:
            res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
            if res.data and p == str(res.data[0].get('senha', '12345')):
                st.session_state.auth = True; st.session_state.perfil = "cliente"; st.session_state.usuario = res.data[0]['nome_fantasia']; st.rerun()
            else: st.error("❌ Credenciais inválidas.")
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    res_est = conn.table("estabelecimentos").select("*").execute()
    todos_lojistas = sorted([e['nome_fantasia'] for e in res_est.data]) if res_est.data else []
    
    d_sel = st.sidebar.date_input("Data do Filtro", date.today())
    menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- ABA GESTÃO (FIX DE EDIÇÃO) ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão de Estabelecimentos")
        t1, t2, t3 = st.tabs(["📋 Visualizar/Editar", "➕ Novo", "🗑️ Excluir"])
        
        with t1:
            if res_est.data:
                df_est = pd.DataFrame(res_est.data)
                # Configura colunas e desabilita ID para edição
                df_editado = st.data_editor(df_est, use_container_width=True, hide_index=True, key="editor_v239",
                                           column_config={"id": st.column_config.Column(disabled=True)})
                
                if st.button("💾 Salvar Alterações"):
                    # Lógica segura de comparação por ID
                    for idx, row in df_editado.iterrows():
                        row_id = row['id']
                        # Busca o original pelo ID
                        original_row = df_est[df_est['id'] == row_id].iloc[0]
                        
                        # Se houver diferença entre a linha do editor e a original
                        if not row.equals(original_row):
                            conn.table("estabelecimentos").update({
                                "nome_fantasia": str(row['nome_fantasia']).upper(),
                                "email": str(row['email']).lower(),
                                "cnpj_cpf": str(row['cnpj_cpf']) if row['cnpj_cpf'] else None,
                                "senha": str(row['senha'])
                            }).eq("id", row_id).execute()
                    
                    st.success("✅ Alterações salvas!"); st.rerun()

        with t2:
            with st.form("add"):
                st.subheader("Novo Cliente")
                n, e, c, s = st.text_input("Nome Fantasia"), st.text_input("Email"), st.text_input("CNPJ/CPF"), st.text_input("Senha", "12345")
                if st.form_submit_button("CADASTRAR"):
                    if n and e:
                        conn.table("estabelecimentos").insert({"nome_fantasia": n.upper().strip(), "email": e.lower().strip(), "cnpj_cpf": c, "senha": s}).execute()
                        st.success("✅ Cadastrado!"); st.rerun()

        with t3:
            if todos_lojistas:
                rem = st.selectbox("Remover lojista:", todos_lojistas)
                if st.button("❌ EXCLUIR PERMANENTEMENTE"):
                    conn.table("estabelecimentos").delete().eq("nome_fantasia", rem).execute()
                    st.success(f"Removido!"); st.rerun()

    # --- DASHBOARD ---
    elif menu == "🏠 Dashboard":
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=300000, key="refresh_v239")
        st.title("📊 Dashboard Financeiro")
        data_txt = d_sel.strftime('%d/%m/%Y')
        v_res = conn.table("vendas").select("*").ilike("data_venda", f"%{data_txt}%").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()

        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
            df_t, df_p = pd.DataFrame(t_res.data), pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})
            df_v['link'], df_m['link'] = df_v['ns'].apply(limpar_ns), df_m['ns'].apply(limpar_ns)
            df = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='left')
            df['nome_lojista'] = df['nome_lojista'].fillna("NAO VINCULADO")
            
            opcoes = sorted(df['nome_lojista'].unique())
            esc = st.sidebar.multiselect("Lojistas:", opcoes, default=opcoes) if st.session_state.perfil == "admin" else [st.session_state.usuario]
            df_f = df[df['nome_lojista'].isin(esc)].copy()

            if not df_f.empty:
                df_f = pd.merge(df_f, df_p, on='nome_plano', how='left')
                def norm_pl(row):
                    p = str(row['plano']).lower()
                    if 'débito' in p or 'debito' in p: return 'débito'
                    if 'pix' in p: return 'pix'
                    if 'à vista' in p or 'a vista' in p or ('crédito' in p and 'x' not in p): return 'à vista'
                    m = re.findall(r'\d+', p)
                    return f"em {m[0]}x" if m else 'à vista'
                df_f['pl_adj'] = df_f.apply(norm_pl, axis=1)
                df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df_f = pd.merge(df_f, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                df_f['bruto_v'] = pd.to_numeric(df_f['bruto'], errors='coerce').fillna(0)
                df_f['t_cli'] = pd.to_numeric(df_f['taxa_decimal'], errors='coerce').fillna(0)
                df_f['liq_v'] = (df_f['bruto_v'] * (1 - df_f['t_cli'])).round(2)
                df_f['taxa_txt'] = (df_f['t_cli'] * 100).map("{:.2f}%".format)
                
                k1, k2, k3 = st.columns(3)
                vb, vl, vq = df_f['bruto_v'].sum(), df_f['liq_v'].sum(), len(df_f)
                k1.metric("Bruto Total", f"R$ {vb:,.2f}"); k2.metric("Liquido Total", f"R$ {vl:,.2f}"); k3.metric("Vendas", vq)
                
                st.divider()
                try:
                    pdf_bytes = gerar_pdf_v239(df_f, data_txt, vb, vl, vq)
                    st.download_button("📄 PDF Detalhado", pdf_bytes, f"Relatorio_{data_txt.replace('/','_')}.pdf", "application/pdf", use_container_width=True)
                except: st.error("Erro no PDF.")
                st.dataframe(df_f[['data_venda', 'nome_lojista', 'ns', 'bandeira', 'plano', 'taxa_txt', 'bruto_v', 'liq_v']], use_container_width=True)
        else: st.info(f"Sem vendas.")

    # Mantendo abas Vincular e Planos...
    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina")
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vinc"):
            c = st.selectbox("Cliente", todos_lojistas)
            ns_txt = st.text_area("NS / IDs Terminal")
            pl = st.selectbox("Plano", sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else ["PADRAO"])
            if st.form_submit_button("Salvar"):
                for n in ns_txt.split(","):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar_ns(n), "nome_lojista": c, "nome_plano": pl}).execute()
                st.success("Vinculado!"); st.rerun()

    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        res_p = conn.table("planos_mj").select("*").execute()
        lista_p = sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else []
        t1, t2 = st.tabs(["📋 Ver", "⚙️ Editar"])
        with t1:
            if lista_p:
                ps = st.selectbox("Plano:", lista_p); id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_tax = pd.DataFrame(res_t.data); df_tax['%'] = df_tax['taxa_decimal'].apply(lambda x: f"{x*100:.2f}%")
                    st.dataframe(pd.pivot_table(df_tax, values='%', index='meio', columns='bandeira', aggfunc='first').fillna("-"), use_container_width=True)
        with t2:
            modo = st.radio("Ação:", ["Novo", "Editar"], horizontal=True)
            nome_f = st.selectbox("Plano:", lista_p) if modo == "Editar" else st.text_input("Nome do Plano")
            band_s = st.selectbox("Bandeira:", ["mastercard", "visa", "elo", "amex", "hipercard", "pix", "picpay"])
            mods = ["pix"] if band_s == "pix" else ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
            df_ed = st.data_editor(pd.DataFrame({"Meio": mods, "Taxa (%)": 0.0}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Plano"):
                p_res = conn.table("planos_mj").upsert({"nome_plano": nome_f.upper()}, on_conflict="nome_plano").execute()
                id_f = p_res.data[0]['id']
                conn.table("taxas_dos_planos").delete().eq("id_plano", id_f).eq("bandeira", band_s).execute()
                batch = [{"id_plano": id_f, "bandeira": band_s, "meio": r['Meio'], "taxa_decimal": float(r['Taxa (%)'])/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute()
                st.success("Salvo!"); st.rerun()

st.sidebar.caption("MJ Soluções v239.0")
