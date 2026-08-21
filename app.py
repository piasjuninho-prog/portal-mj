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

# --- FUNÇÕES DE AUXÍLIO ---
def limpar_ns(val):
    if not val: return ""
    return re.sub(r'[^A-Z0-9]', '', str(val).strip().upper()).lstrip('0')

def safe_text(text):
    """Limpeza para evitar erro de caracteres no PDF"""
    if text is None: return ""
    # Remove acentos e emojis
    nfkd_form = unicodedata.normalize('NFKD', str(text))
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).encode('ascii', 'ignore').decode('ascii')

def gerar_pdf_bytes(df, data_ref, bruto, liquido, qtd):
    # Com fpdf2, o output() retorna bytes automaticamente
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(190, 10, safe_text("MJ SOLUCOES - RELATORIO FINANCEIRO"), 0, 1, 'C')
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(190, 7, f"Data: {data_ref}", 0, 1, 'C')
    pdf.ln(10)
    
    # Resumo
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(190, 10, " RESUMO GERAL", 1, 1, 'L', 1)
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(63, 10, f"Bruto: RS {bruto:,.2f}", 1, 0, 'C')
    pdf.cell(63, 10, f"Liquido: RS {liquido:,.2f}", 1, 0, 'C')
    pdf.cell(64, 10, f"Vendas: {qtd}", 1, 1, 'C')
    pdf.ln(5)
    
    # Tabela
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(25, 8, "Data", 1, 0, 'C', 1)
    pdf.cell(70, 8, "Lojista", 1, 0, 'C', 1)
    pdf.cell(25, 8, "Band.", 1, 0, 'C', 1)
    pdf.cell(35, 8, "Bruto", 1, 0, 'C', 1)
    pdf.cell(35, 8, "Liquido", 1, 1, 'C', 1)
    
    pdf.set_font("Helvetica", '', 8)
    for _, row in df.iterrows():
        pdf.cell(25, 7, safe_text(row['data_venda']), 1, 0, 'C')
        pdf.cell(70, 7, safe_text(str(row['nome_lojista'])[:30]), 1, 0, 'L')
        pdf.cell(25, 7, safe_text(row['bandeira']), 1, 0, 'C')
        pdf.cell(35, 7, f"{row['bruto_v']:,.2f}", 1, 0, 'R')
        pdf.cell(35, 7, f"{row['liq_v']:,.2f}", 1, 1, 'R')
    
    # pdf.output() no fpdf2 sem argumentos gera bytes
    return pdf.output()

# --- LOGIN E SIDEBAR ---
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
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    d_sel = st.sidebar.date_input("Data do Filtro", date.today())
    menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    elif menu == "🏠 Dashboard":
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=300000, key="refresh_v230")
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
            
            df_v['link'] = df_v['ns'].apply(limpar_ns)
            df_m['link'] = df_m['ns'].apply(limpar_ns)
            df = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='left')
            df['nome_lojista'] = df['nome_lojista'].fillna("NAO VINCULADO")

            opcoes_lojistas = sorted(df['nome_lojista'].unique())
            if st.session_state.perfil == "admin":
                esc_lojistas = st.sidebar.multiselect("Filtrar Lojistas:", opcoes_lojistas, default=opcoes_lojistas)
            else:
                esc_lojistas = [st.session_state.usuario]

            df_f = df[df['nome_lojista'].isin(esc_lojistas)].copy()

            if not df_f.empty:
                df_f = pd.merge(df_f, df_p, on='nome_plano', how='left')
                
                def norm_pl(row):
                    p = str(row['plano']).lower()
                    if 'debito' in p: return 'debito'
                    if 'pix' in p: return 'pix'
                    m = re.findall(r'\d+', p)
                    return f"em {m[0]}x" if m else 'a vista'
                
                df_f['pl_adj'] = df_f.apply(norm_pl, axis=1)
                df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df_f = pd.merge(df_f, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                
                df_f['bruto_v'] = pd.to_numeric(df_f['bruto'], errors='coerce').fillna(0)
                df_f['t_cli'] = pd.to_numeric(df_f['taxa_decimal'], errors='coerce').fillna(0)
                df_f['liq_v'] = (df_f['bruto_v'] * (1 - df_f['t_cli'])).round(2)
                df_f['taxa_txt'] = (df_f['t_cli'] * 100).map("{:.2f}%".format)

                st.success(f"Vendas encontradas: {len(df_f)}")
                k1, k2, k3 = st.columns(3)
                vb, vl, vq = df_f['bruto_v'].sum(), df_f['liq_v'].sum(), len(df_f)
                k1.metric("Bruto Total", f"R$ {vb:,.2f}")
                k2.metric("Liquido Total", f"R$ {vl:,.2f}")
                k3.metric("Qtd Vendas", vq)
                
                # --- BOTÃO PDF v230 ---
                st.divider()
                try:
                    pdf_bytes = gerar_pdf_bytes(df_f, data_txt, vb, vl, vq)
                    st.download_button(
                        label="📄 Baixar Relatorio PDF",
                        data=pdf_bytes,
                        file_name=f"Relatorio_{data_txt.replace('/','_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro no PDF. Certifique-se de que fpdf2 esta no requirements.txt.")

                st.dataframe(df_f[['data_venda', 'nome_lojista', 'adquirente', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)

    # --- ABAS GESTÃO, VINCULAR E PLANOS ---
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
                    df_tax = pd.DataFrame(res_t.data)
                    df_tax['%'] = df_tax['taxa_decimal'].apply(lambda x: f"{x*100:.2f}%")
                    st.dataframe(pd.pivot_table(df_tax, values='%', index='meio', columns='bandeira', aggfunc='first').reindex(index=ORDEM_MODALIDADES, columns=ORDEM_BANDEIRAS).fillna("-"), use_container_width=True)
        with t2:
            modo = st.radio("Ação:", ["Novo", "Editar"], horizontal=True)
            nome_f = st.selectbox("Plano:", lista_p) if modo == "Editar" else st.text_input("Nome do Plano")
            band_s = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
            mods = ["pix"] if band_s == "pix" else ORDEM_MODALIDADES
            df_ed = st.data_editor(pd.DataFrame({"Meio": mods, "Venda (%)": 0.0, "Custo (%)": 0.0}), use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Bandeira"):
                p_res = conn.table("planos_mj").upsert({"nome_plano": nome_f.upper().strip()}, on_conflict="nome_plano").execute()
                id_f = p_res.data[0]['id']
                conn.table("taxas_dos_planos").delete().eq("id_plano", id_f).eq("bandeira", band_s).execute()
                batch = [{"id_plano": id_f, "bandeira": band_s, "meio": r['Meio'], "taxa_decimal": float(r['Venda (%)'])/100, "custo_decimal": float(r['Custo (%)'])/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute()
                st.success("✅ Salvo!"); st.rerun()

    elif menu == "👤 Vincular":
        st.title("👤 Vincular Máquina")
        res_p = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vinc"):
            c = st.selectbox("Cliente", todos_lojistas)
            ns_txt = st.text_area("NS / IDs Terminal (separe por vírgula)")
            pl = st.selectbox("Plano", sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else ["PADRAO"])
            if st.form_submit_button("Salvar"):
                for n in ns_txt.split(","):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar_ns(n), "nome_lojista": c, "nome_plano": pl}).execute()
                st.success("✅ Vinculado!"); st.rerun()

st.sidebar.caption("MJ Soluções v230.0")
