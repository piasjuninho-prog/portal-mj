import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
import re
import unicodedata
from fpdf import FPDF
from io import BytesIO

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

def safe_pdf_text(text):
    """Converte qualquer texto para ASCII puro para evitar falha no download"""
    if text is None: return ""
    # Remove acentos (ã -> a)
    normalized = unicodedata.normalize('NFKD', str(text))
    # Filtra apenas caracteres básicos
    ascii_text = "".join([c for c in normalized if not unicodedata.combining(c)])
    # Remove emojis e caracteres especiais, mantendo apenas o essencial
    return ascii_text.encode('ascii', 'ignore').decode('ascii').replace('$', 'RS')

def gerar_pdf_final(df, data_ref, bruto, liquido, qtd):
    pdf = FPDF()
    pdf.add_page()
    
    # Configurações de fonte padrão
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(190, 10, safe_pdf_text("MJ SOLUCOES - RELATORIO FINANCEIRO"), 0, 1, 'C')
    
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(190, 7, f"Data: {data_ref}", 0, 1, 'C')
    pdf.ln(10)
    
    # Bloco de Resumo
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(190, 10, " RESUMO GERAL", 1, 1, 'L', 1)
    
    pdf.set_font("Helvetica", '', 12)
    # Formatamos os números antes de enviar para o PDF
    pdf.cell(63, 10, safe_pdf_text(f"Bruto: RS {bruto:,.2f}"), 1, 0, 'C')
    pdf.cell(63, 10, safe_pdf_text(f"Liquido: RS {liquido:,.2f}"), 1, 0, 'C')
    pdf.cell(64, 10, safe_pdf_text(f"Vendas: {qtd}"), 1, 1, 'C')
    pdf.ln(5)
    
    # Cabeçalho da Tabela
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(25, 8, "Data", 1, 0, 'C', 1)
    pdf.cell(70, 8, "Estabelecimento", 1, 0, 'C', 1)
    pdf.cell(25, 8, "Band.", 1, 0, 'C', 1)
    pdf.cell(35, 8, "Bruto (RS)", 1, 0, 'C', 1)
    pdf.cell(35, 8, "Liq. (RS)", 1, 1, 'C', 1)
    
    # Dados da Tabela
    pdf.set_font("Helvetica", '', 8)
    for _, row in df.iterrows():
        pdf.cell(25, 7, safe_pdf_text(row['data_venda']), 1, 0, 'C')
        pdf.cell(70, 7, safe_pdf_text(str(row['nome_lojista'])[:30]), 1, 0, 'L')
        pdf.cell(25, 7, safe_pdf_text(row['bandeira']), 1, 0, 'C')
        pdf.cell(35, 7, f"{row['bruto_v']:,.2f}", 1, 0, 'R')
        pdf.cell(35, 7, f"{row['liq_v']:,.2f}", 1, 1, 'R')
    
    # O SEGREDO: Saída em Bytes usando buffer BytesIO para evitar falha de download
    return pdf.output()

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
    d_sel = st.sidebar.date_input("Data do Filtro", date.today())
    menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- DASHBOARD ---
    elif menu == "🏠 Dashboard":
        from streamlit_autorefresh import st_autorefresh
        # Refresh de 5 minutos (evita resetar a página durante o download)
        st_autorefresh(interval=300000, key="refresh_v229")
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
                
                # Puxar taxas e calcular
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
                
                # --- BOTÃO PDF v229 ---
                st.divider()
                try:
                    # Geramos o binário do PDF
                    binario_pdf = gerar_pdf_final(df_f, data_txt, vb, vl, vq)
                    
                    st.download_button(
                        label="📄 Baixar Relatorio PDF",
                        data=binario_pdf,
                        file_name=f"Relatorio_{data_txt.replace('/','_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

                st.dataframe(df_f[['data_venda', 'nome_lojista', 'adquirente', 'bandeira', 'plano', 'bruto_v', 'taxa_txt', 'liq_v']], use_container_width=True)
            else:
                st.warning("Selecione os lojistas.")
        else:
            st.info(f"Sem vendas para {data_txt}.")

st.sidebar.caption("MJ Soluções v229.0")
