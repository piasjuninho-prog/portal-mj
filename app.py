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
    # --- INTERFACE ---
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    res_est = conn.table("estabelecimentos").select("*").execute()
    todos_lojistas = sorted([e['nome_fantasia'] for e in res_est.data]) if res_est.data else []
    d_sel = st.sidebar.date_input("Data do Filtro", date.today())
    menu = st.sidebar.radio("MENU", ["🏠 Dashboard", "👤 Vincular", "🏫 Gestão", "📂 Planos", "🚪 Sair"])
    if menu == "🚪 Sair": st.session_state.auth = False; st.rerun()

    # --- ABA DASHBOARD (v245 - AUDITORIA) ---
    elif menu == "🏠 Dashboard":
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=300000, key="refresh_v245")
        st.title("📊 Dashboard Financeiro")
        data_txt = d_sel.strftime('%d/%m/%Y')
        
        # 1. Coleta dados brutos das vendas do dia
        v_res = conn.table("vendas").select("*").ilike("data_venda", f"%{data_txt}%").execute()
        m_res = conn.table("maquinas_ns").select("*").execute()
        p_res = conn.table("planos_mj").select("id, nome_plano").execute()
        t_res = conn.table("taxas_dos_planos").select("*").execute()

        if v_res.data:
            df_v = pd.DataFrame(v_res.data)
            df_m = pd.DataFrame(m_res.data) if m_res.data else pd.DataFrame(columns=['ns', 'nome_lojista', 'nome_plano'])
            df_v['link'], df_m['link'] = df_v['ns'].apply(limpar_ns), df_m['ns'].apply(limpar_ns)
            
            # --- SEÇÃO DE AUDITORIA (VERIFICA MAQUINAS SEM VÍNCULO) ---
            # Cruzamos as vendas com o cadastro de máquinas
            df_audit = pd.merge(df_v, df_m[['link', 'nome_lojista']], on='link', how='left')
            
            vendas_sem_dono = df_audit[df_audit['nome_lojista'].isna()]
            
            if not vendas_sem_dono.empty:
                st.error("🚨 **ALERTA DE VENDAS SEM VÍNCULO!**")
                st.write("O robô enviou as seguintes máquinas, mas elas não estão cadastradas no portal:")
                # Agrupa por NS para facilitar a cópia
                resumo_sem_vinc = vendas_sem_dono.groupby('ns').agg({'bruto': ['count', 'sum']}).reset_index()
                resumo_sem_vinc.columns = ['Número de Série (NS)', 'Qtd Vendas', 'Valor Total (R$)']
                st.table(resumo_sem_vinc)
                st.info("💡 Copie os NS acima e vincule-os a um cliente na aba **👤 Vincular**.")
                st.divider()
            else:
                st.success(f"✅ Todas as {len(df_v)} vendas de hoje estão devidamente vinculadas!")

            # --- PROSSEGUIR COM O DASHBOARD ---
            df_m_info = df_m[['link', 'nome_lojista', 'nome_plano']]
            df = pd.merge(df_v, df_m_info, on='link', how='inner') # Aqui usamos inner para mostrar apenas o que tem dono nos filtros
            
            if not df.empty:
                opcoes = sorted(df['nome_lojista'].unique())
                esc = st.sidebar.multiselect("Filtrar Lojistas:", opcoes, default=opcoes) if st.session_state.perfil == "admin" else [st.session_state.usuario]
                df_f = df[df['nome_lojista'].isin(esc)].copy()

                if not df_f.empty:
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
                st.warning("Vendas encontradas no banco, mas nenhuma está vinculada a lojistas.")
        else:
            st.info(f"O banco de dados está vazio para o dia {data_txt}.")

    # --- ABA GESTÃO, VINCULAR, PLANOS ---
    elif menu == "🏫 Gestão":
        st.title("🏫 Gestão")
        df_est = pd.DataFrame(res_est.data)
        df_ed = st.data_editor(df_est, use_container_width=True, hide_index=True, key="ed_gest", column_config={"id": st.column_config.Column(disabled=True)})
        if st.button("💾 Salvar Alterações"):
            for idx, row in df_ed.iterrows():
                conn.table("estabelecimentos").update({"nome_fantasia": str(row['nome_fantasia']).upper(), "email": str(row['email']).lower(), "senha": str(row['senha'])}).eq("id", row['id']).execute()
            st.rerun()
        if todos_lojistas:
            rem = st.selectbox("Excluir Lojista:", todos_lojistas)
            if st.button("❌ EXCLUIR"): conn.table("estabelecimentos").delete().eq("nome_fantasia", rem).execute(); st.rerun()

    elif menu == "📂 Planos":
        st.title("📂 Planos de Taxas")
        res_p = conn.table("planos_mj").select("*").execute(); lista_p = sorted([p['nome_plano'] for p in res_p.data])
        t1, t2 = st.tabs(["📋 Ver", "⚙️ Editar"])
        with t1:
            if lista_p:
                ps = st.selectbox("Plano:", lista_p, key="v_pl"); id_p = next(p['id'] for p in res_p.data if p['nome_plano'] == ps)
                res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                if res_t.data:
                    df_t = pd.DataFrame(res_t.data); df_t['Taxa%'] = df_t['taxa_decimal'].apply(lambda x: f"{x*100:.2f}%")
                    st.dataframe(pd.pivot_table(df_t, values='Taxa%', index='meio', columns='bandeira', aggfunc='first').reindex(index=ORDEM_MODALIDADES).dropna(how='all'), use_container_width=True)
        with t2:
            modo = st.radio("Ação:", ["Editar", "Novo"], horizontal=True)
            nome_f = st.selectbox("Plano:", lista_p, key="e_pl") if modo == "Editar" else st.text_input("Nome:")
            band_s = st.selectbox("Bandeira:", ORDEM_BANDEIRAS)
            id_f = next((p['id'] for p in res_p.data if p['nome_plano'] == nome_f), None)
            res_atuais = conn.table("taxas_dos_planos").select("meio, taxa_decimal, custo_decimal").eq("id_plano", id_f).eq("bandeira", band_s).execute() if id_f else None
            df_base = pd.DataFrame({"Meio": ORDEM_MODALIDADES if band_s != "pix" else ["pix"], "Venda (%)": 0.0, "Custo (%)": 0.0})
            if res_atuais and res_atuais.data:
                df_a = pd.DataFrame(res_atuais.data); df_a['Venda (%)'], df_a['Custo (%)'] = df_a['taxa_decimal']*100, df_a['custo_decimal']*100
                df_base = pd.merge(df_base[['Meio']], df_a[['meio', 'Venda (%)', 'Custo (%)']], left_on='Meio', right_on='meio', how='left').fillna(0)[['Meio', 'Venda (%)', 'Custo (%)']]
            df_ed = st.data_editor(df_base, use_container_width=True, hide_index=True)
            if st.button("💾 Salvar Plano"):
                p_res = conn.table("planos_mj").upsert({"nome_plano": nome_f.upper()}, on_conflict="nome_plano").execute()
                id_f = p_res.data[0]['id']
                conn.table("taxas_dos_planos").delete().eq("id_plano", id_f).eq("bandeira", band_s).execute()
                batch = [{"id_plano": id_f, "bandeira": band_s, "meio": r['Meio'], "taxa_decimal": float(r['Venda (%)'])/100, "custo_decimal": float(r['Custo (%)'])/100} for _, r in df_ed.iterrows()]
                conn.table("taxas_dos_planos").insert(batch).execute(); st.success("Salvo!"); st.rerun()

    elif menu == "👤 Vincular":
        st.title("👤 Vincular")
        res_lo = conn.table("estabelecimentos").select("nome_fantasia").execute()
        res_pl = conn.table("planos_mj").select("nome_plano").execute()
        with st.form("vinc"):
            c = st.selectbox("Lojista:", sorted([l['nome_fantasia'] for l in res_lo.data]))
            ns_txt = st.text_area("NS / IDs"); pl = st.selectbox("Plano:", sorted([p['nome_plano'] for p in res_pl.data]))
            if st.form_submit_button("VINCULAR"):
                for n in ns_txt.split(","):
                    if n.strip(): conn.table("maquinas_ns").upsert({"ns": limpar_ns(n), "nome_lojista": c, "nome_plano": pl}).execute()
                st.success("Vinculado!"); st.rerun()

st.sidebar.caption("MJ Soluções v245.0")
