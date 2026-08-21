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

# --- FUNÇÃO DE LIMPEZA RADICAL PARA PDF ---
def clean_pdf_text(text):
    """Transforma qualquer texto em ASCII puro (sem acentos ou simbolos)"""
    if not text: return ""
    # Remove acentos (Ex: 'ã' -> 'a')
    nfkd_form = unicodedata.normalize('NFKD', str(text))
    text_ascii = nfkd_form.encode('ascii', 'ignore').decode('ascii')
    # Remove R$ e outros simbolos que podem travar o download
    return text_ascii.replace('$', 'RS').replace('=', '-').strip()

def gerar_pdf(df, data_ref, bruto, liquido, qtd):
    pdf = FPDF()
    pdf.add_page()
    
    # Titulo
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(190, 10, clean_pdf_text("MJ SOLUCOES - RELATORIO FINANCEIRO"), 0, 1, 'C')
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(190, 7, f"Data: {data_ref}", 0, 1, 'C')
    pdf.ln(10)
    
    # Resumo Financeiro
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(190, 10, " RESUMO GERAL", 1, 1, 'L', 1)
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(63, 10, clean_pdf_text(f"Bruto: RS {bruto:,.2f}"), 1, 0, 'C')
    pdf.cell(63, 10, clean_pdf_text(f"Liquido: RS {liquido:,.2f}"), 1, 0, 'C')
    pdf.cell(64, 10, clean_pdf_text(f"Vendas: {qtd}"), 1, 1, 'C')
    pdf.ln(10)
    
    # Cabeçalho Tabela
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(25, 8, "Data", 1, 0, 'C', 1)
    pdf.cell(75, 8, "Lojista", 1, 0, 'C', 1)
    pdf.cell(25, 8, "Bandeira", 1, 0, 'C', 1)
    pdf.cell(35, 8, "Bruto", 1, 0, 'C', 1)
    pdf.cell(30, 8, "Liquido", 1, 1, 'C', 1)
    
    # Linhas
    pdf.set_font("Helvetica", '', 8)
    for _, row in df.iterrows():
        pdf.cell(25, 7, clean_pdf_text(row['data_venda']), 1, 0, 'C')
        pdf.cell(75, 7, clean_pdf_text(row['nome_lojista'][:35]), 1, 0, 'L')
        pdf.cell(25, 7, clean_pdf_text(row['bandeira']), 1, 0, 'C')
        pdf.cell(35, 7, clean_pdf_text(f"RS {row['bruto_v']:,.2f}"), 1, 0, 'R')
        pdf.cell(30, 7, clean_pdf_text(f"RS {row['liq_v']:,.2f}"), 1, 1, 'R')
        
    # Retorna os bytes puros
    return bytes(pdf.output())

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

    # --- DASHBOARD (v225) ---
    elif menu == "🏠 Dashboard":
        from streamlit_autorefresh import st_autorefresh
        # Refresh de 2 minutos (para não atrapalhar o download)
        st_autorefresh(interval=120000, key="refresh_v225")
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
            
            def limpar_ns_local(val):
                return re.sub(r'[^A-Z0-9]', '', str(val).strip().upper()).lstrip('0')

            df_v['link'] = df_v['ns'].apply(limpar_ns_local)
            df_m['link'] = df_m['ns'].apply(limpar_ns_local)
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
                
                # Normalização simplificada de taxas
                df_f['bruto_v'] = pd.to_numeric(df_f['bruto'], errors='coerce').fillna(0)
                df_f['t_cli'] = pd.to_numeric(df_f['taxa_decimal'], errors='coerce').fillna(0)
                df_f['liq_v'] = (df_f['bruto_v'] * (1 - df_f['t_cli'])).round(2)
                df_f['taxa_txt'] = (df_f['t_cli'] * 100).map("{:.2f}%".format)

                st.success(f"Encontradas {len(df_f)} vendas.")
                k1, k2, k3 = st.columns(3)
                vb, vl, vq = df_f['bruto_v'].sum(), df_f['liq_v'].sum(), len(df_f)
                k1.metric("Bruto Total", f"RS {vb:,.2f}")
                k2.metric("Liquido Total", f"RS {vl:,.2f}")
                k3.metric("Qtd Vendas", vq)
                
                # --- BOTÃO PDF SEGURO ---
                st.divider()
                try:
                    pdf_bytes = gerar_pdf(df_f, data_txt, vb, vl, vq)
                    st.download_button(
                        label="📄 Baixar Relatorio PDF",
                        data=pdf_bytes,
                        file_name=f"Relatorio_MJ_{data_txt.replace('/','_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro na geração do arquivo. Verifique os nomes dos lojistas.")

                st.dataframe(df_f[['data_venda', 'nome_lojista', 'adquirente', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)
            else:
                st.warning("Selecione os lojistas.")
        else:
            st.info(f"Sem vendas para {data_txt}.")

st.sidebar.caption("MJ Soluções v225.0")
