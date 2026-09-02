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

# --- FUNÇÕES ---
def limpar_ns(val):
    if not val: return ""
    return re.sub(r'[^A-Z0-9]', '', str(val).strip().upper()).lstrip('0')

def safe_text(text):
    if text is None: return ""
    nfkd_form = unicodedata.normalize('NFKD', str(text))
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).encode('ascii', 'ignore').decode('ascii')

def gerar_pdf_final(df, data_ref, bruto, liquido, lucro, qtd, perfil):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 18)
    pdf.cell(277, 10, safe_text("MJ SOLUCOES - RELATORIO FINANCEIRO"), 0, 1, 'C')
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240); pdf.set_font("Helvetica", 'B', 12)
    resumo = f" Bruto: RS {bruto:,.2f}  |  Liquido: RS {liquido:,.2f} | Vendas: {qtd}"
    pdf.cell(277, 10, safe_text(resumo), 1, 1, 'C', 1)
    pdf.ln(5)
    cols = [("Data", 25), ("Lojista", 55), ("NS", 35), ("Band", 20), ("Plano", 40), ("Taxa%", 22), ("Bruto", 30), ("Liq", 30)]
    pdf.set_font("Helvetica", 'B', 9); pdf.set_fill_color(200, 200, 200)
    for c, w in cols: pdf.cell(w, 8, c, 1, 0, 'C', 1)
    pdf.ln()
    pdf.set_font("Helvetica", '', 8)
    for _, r in df.iterrows():
        pdf.cell(25, 7, safe_text(r['data_venda']), 1, 0, 'C')
        pdf.cell(55, 7, safe_text(str(r['nome_lojista'])[:25]), 1, 0, 'L')
        pdf.cell(35, 7, safe_text(r['ns']), 1, 0, 'C')
        pdf.cell(20, 7, safe_text(r['bandeira']), 1, 0, 'C')
        pdf.cell(40, 7, safe_text(r['plano']), 1, 0, 'C')
        pdf.cell(22, 7, safe_text(r['taxa_txt']), 1, 0, 'C')
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
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    res_est = conn.table("estabelecimentos").select("*").execute()
    todos_lojistas = sorted([e['nome_fantasia'] for e in res_est.data]) if res_est.data else []
    d_sel = st.sidebar.date_input("Data do Filtro", date.today())
    menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- ABA DASHBOARD (v246 - DEBUG DE DONOS) ---
    elif menu == "🏠 Dashboard":
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=300000, key="refresh_v246")
        st.title("📊 Dashboard Financeiro")
        data_txt = d_sel.strftime('%d/%m/%Y')
        
        v_res = conn.table("vendas").select("*").ilike("data_venda", f"%{data_txt}%").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        
        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
            df_v['link'], df_m['link'] = df_v['ns'].apply(limpar_ns), df_m['ns'].apply(limpar_ns)
            
            # Cruzamento completo (Left Join) para auditoria
            df_audit = pd.merge(df_v, df_m[['link', 'nome_lojista', 'nome_plano']], on='link', how='left')
            df_audit['nome_lojista'] = df_audit['nome_lojista'].fillna("⚠️ NÃO VINCULADO")
            
            # --- BARRA DE AUDITORIA INTELIGENTE ---
            total_vendas = len(df_audit)
            vendas_sem_dono = df_audit[df_audit['nome_lojista'] == "⚠️ NÃO VINCULADO"]
            
            if not vendas_sem_dono.empty:
                st.error(f"🚨 **EXISTEM {len(vendas_sem_dono)} VENDAS SEM VÍNCULO!**")
                st.write("Números de Série (NS) que precisam ser cadastrados:")
                st.table(vendas_sem_dono.groupby(['ns', 'adquirente']).size().reset_index(name='Qtd'))
                st.divider()
            else:
                with st.expander(f"✅ Todas as {total_vendas} vendas de hoje estão vinculadas. Clique para ver o resumo por dono:"):
                    # Aqui você vai descobrir quem são os donos das 32 vendas
                    resumo_donos = df_audit.groupby(['nome_lojista', 'adquirente']).agg({'bruto': ['count', 'sum']}).reset_index()
                    resumo_donos.columns = ['Lojista', 'Adquirente', 'Qtd Vendas', 'Total Bruto (R$)']
                    st.table(resumo_donos)

            # --- FILTROS SIDEBAR ---
            opcoes = sorted(df_audit['nome_lojista'].unique())
            esc = st.sidebar.multiselect("Filtrar Lojistas:", opcoes, default=opcoes) if st.session_state.perfil == "admin" else [st.session_state.usuario]
            
            df_f = df_audit[df_audit['nome_lojista'].isin(esc)].copy()

            if not df_f.empty:
                # Puxar Planos e Taxas
                p_res = conn.table("planos_mj").select("id, nome_plano").execute()
                t_res = conn.table("taxas_dos_planos").select("*").execute()
                df_p = pd.DataFrame(p_res.data).rename(columns={'id':'id_p'})
                df_t = pd.DataFrame(t_res.data)
                
                df_f = pd.merge(df_f, df_p, on='nome_plano', how='left')
                
                def norm_pl(row):
                    p = str(row['plano']).lower()
                    if 'débito' in p or 'debito' in p: return 'débito'
                    if 'pix' in p: return 'pix'
                    if 'à vista' in p or 'a vista' in p or ('crédito' in p and 'x' not in p): return 'à vista'
                    m = re.findall(r'\d+', p); return f"em {m[0]}x" if m else 'à vista'
                
                df_f['pl_adj'] = df_f.apply(norm_pl, axis=1)
                df_t_c = df_t.drop_duplicates(subset=['id_plano','bandeira','meio']).rename(columns={'bandeira':'b_p','meio':'m_p'})
                df_f = pd.merge(df_f, df_t_c, left_on=['id_p','bandeira','pl_adj'], right_on=['id_plano','b_p','m_p'], how='left')
                
                df_f['bruto_v'] = pd.to_numeric(df_f['bruto'], errors='coerce').fillna(0)
                df_f['t_cli'] = pd.to_numeric(df_f['taxa_decimal'], errors='coerce').fillna(0)
                df_f['t_cus'] = pd.to_numeric(df_f.get('custo_decimal', 0), errors='coerce').fillna(0)
                df_f['liq_v'] = (df_f['bruto_v'] * (1 - df_f['t_cli'])).round(2)
                df_f['lucro_v'] = (df_f['bruto_v'] * (df_f['t_cli'] - df_f['t_cus'])).round(2)
                df_f['taxa_txt'] = (df_f['t_cli'] * 100).map("{:.2f}%".format)

                c1, c2, c3, c4 = st.columns(4)
                vb, vl, vlu, vq = df_f['bruto_v'].sum(), df_f['liq_v'].sum(), df_f['lucro_v'].sum(), len(df_f)
                c1.metric("Bruto Total", f"R$ {vb:,.2f}"); c2.metric("Liquido Total", f"R$ {vl:,.2f}"); c3.metric("Vendas", vq)
                if st.session_state.perfil == "admin": c4.metric("Lucro MJ", f"R$ {vlu:,.2f}")

                st.divider()
                try:
                    pdf = gerar_pdf_final(df_f, data_txt, vb, vl, vlu, vq, st.session_state.perfil)
                    st.download_button("📄 Baixar PDF Detalhado", pdf, f"Relatorio_{data_txt.replace('/','_')}.pdf", "application/pdf", use_container_width=True)
                except: st.error("Erro no PDF.")
                st.dataframe(df_f[['data_venda', 'nome_lojista', 'ns', 'bandeira', 'plano', 'taxa_txt', 'bruto_v', 'liq_v']], use_container_width=True)
        else:
            st.info(f"Sem vendas para {data_txt}.")

    # (Mantenha as abas de Gestão, Vincular e Planos iguais)
    # ...
