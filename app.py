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
    """Limpa textos para evitar erro de caracteres no PDF"""
    if text is None: return ""
    # Transforma acentos em letras simples e remove emojis
    text = str(text)
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).encode('ascii', 'ignore').decode('ascii')

def gerar_pdf_v233(df, data_ref, bruto, liquido, qtd):
    # 'L' = Landscape (Paisagem/Deitado) para caber mais colunas
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Cabeçalho do Relatório
    pdf.set_font("Helvetica", 'B', 18)
    pdf.cell(277, 10, safe_text("MJ SOLUCOES - RELATORIO DETALHADO DE VENDAS"), 0, 1, 'C')
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(277, 7, f"Data das Vendas: {data_ref}", 0, 1, 'C')
    pdf.ln(10)
    
    # Bloco de Resumo Financeiro
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(277, 10, safe_text(" RESUMO DO PERIODO"), 1, 1, 'L', 1)
    
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(92, 10, safe_text(f"Bruto Total: RS {bruto:,.2f}"), 1, 0, 'C')
    pdf.cell(92, 10, safe_text(f"Liquido Total: RS {liquido:,.2f}"), 1, 0, 'C')
    pdf.cell(93, 10, safe_text(f"Qtd Vendas: {qtd}"), 1, 1, 'C')
    pdf.ln(5)
    
    # Cabeçalho da Tabela (Largura total 277mm)
    # Larguras: Data(25), Lojista(55), NS(40), Band(25), Plano(52), Bruto(40), Liquido(40)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(25, 8, "Data", 1, 0, 'C', 1)
    pdf.cell(55, 8, "Lojista", 1, 0, 'C', 1)
    pdf.cell(40, 8, "NS / Terminal", 1, 0, 'C', 1)
    pdf.cell(25, 8, "Band.", 1, 0, 'C', 1)
    pdf.cell(52, 8, "Plano/Parcelas", 1, 0, 'C', 1)
    pdf.cell(40, 8, "Bruto", 1, 0, 'C', 1)
    pdf.cell(40, 8, "Liquido", 1, 1, 'C', 1)
    
    # Linhas da Tabela
    pdf.set_font("Helvetica", '', 8)
    for _, row in df.iterrows():
        pdf.cell(25, 7, safe_text(row['data_venda']), 1, 0, 'C')
        pdf.cell(55, 7, safe_text(str(row['nome_lojista'])[:25]), 1, 0, 'L')
        pdf.cell(40, 7, safe_text(row['ns']), 1, 0, 'C')
        pdf.cell(25, 7, safe_text(row['bandeira']), 1, 0, 'C')
        pdf.cell(52, 7, safe_text(row['plano']), 1, 0, 'C')
        pdf.cell(40, 7, safe_text(f"RS {row['bruto_v']:,.2f}"), 1, 0, 'R')
        pdf.cell(40, 7, safe_text(f"RS {row['liq_v']:,.2f}"), 1, 1, 'R')
        
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
    res_est = conn.table("estabelecimentos").select("nome_fantasia").execute()
    todos_lojistas = sorted([e['nome_fantasia'] for e in res_est.data]) if res_est.data else []
    
    d_sel = st.sidebar.date_input("Data do Filtro", date.today())
    menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- ABA DASHBOARD ---
    elif menu == "🏠 Dashboard":
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=300000, key="refresh_v233")
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

                st.success(f"📦 Encontradas {len(df_f)} vendas.")
                k1, k2, k3 = st.columns(3)
                vb, vl, vq = df_f['bruto_v'].sum(), df_f['liq_v'].sum(), len(df_f)
                k1.metric("Bruto Total", f"R$ {vb:,.2f}")
                k2.metric("Liquido Total", f"R$ {vl:,.2f}")
                k3.metric("Qtd Vendas", vq)
                
                # --- BOTÃO PDF v233 ---
                st.divider()
                try:
                    pdf_bytes = gerar_pdf_v233(df_f, data_txt, vb, vl, vq)
                    st.download_button(
                        label="📄 Baixar Relatorio PDF Detalhado",
                        data=pdf_bytes,
                        file_name=f"Relatorio_MJ_{data_txt.replace('/','_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_pdf_v233"
                    )
                except Exception as e:
                    st.error(f"Erro ao gerar PDF: {e}")

                st.dataframe(df_f[['data_venda', 'nome_lojista', 'ns', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)
            else:
                st.warning("Selecione os lojistas.")
        else:
            st.info(f"Sem vendas para {data_txt}.")

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
        res = conn.table("estabelecimentos").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

    # --- ABA PLANOS ---
    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        modo = st.radio("Ação:", ["Novo", "Editar"], horizontal=True)
        res_p = conn.table("planos_mj").select("*").execute()
        lista_p = sorted([p['nome_plano'] for p in res_p.data]) if res_p.data else []
        nome_f = st.selectbox("Plano:", lista_p) if modo == "Editar" else st.text_input("Nome do Plano")
        band_s = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
        mods = ["pix"] if band_s == "pix" else ORDEM_MODALIDADES
        df_ed = st.data_editor(pd.DataFrame({"Meio": mods, "Venda (%)": 0.0, "Custo (%)": 0.0}), use_container_width=True, hide_index=True)
        if st.button("💾 Salvar"):
            p_res = conn.table("planos_mj").upsert({"nome_plano": nome_f.upper().strip()}, on_conflict="nome_plano").execute()
            id_f = p_res.data[0]['id']
            conn.table("taxas_dos_planos").delete().eq("id_plano", id_f).eq("bandeira", band_s).execute()
            batch = [{"id_plano": id_f, "bandeira": band_s, "meio": r['Meio'], "taxa_decimal": float(r['Venda (%)'])/100, "custo_decimal": float(r['Custo (%)'])/100} for _, r in df_ed.iterrows()]
            conn.table("taxas_dos_planos").insert(batch).execute()
            st.success("✅ Salvo!"); st.rerun()

    # --- ABA VINCULAR ---
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

st.sidebar.caption("MJ Soluções v233.0")
