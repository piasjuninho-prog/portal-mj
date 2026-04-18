import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ Soluções", layout="wide", initial_sidebar_state="expanded")

# --- 1. CONEXÃO (COLE SEUS DADOS REAIS ABAIXO) ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc" 

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função para converter data (InfinitePay e PicPay)
def converter_data(data_str):
    try:
        if not data_str: return None
        d = str(data_str).split(' •')[0].replace(',', '').strip()
        if "/" in d: return pd.to_datetime(d, format='%d/%m/%Y', errors='coerce')
        meses = {'Jan':'01','Fev':'02','Mar':'03','Abr':'04','Mai':'05','Jun':'06','Jul':'07','Ago':'08','Set':'09','Out':'10','Nov':'11','Dez':'12'}
        for pt, num in meses.items():
            if pt in d: d = d.replace(pt, num); break
        return pd.to_datetime(d, format='%d %m %Y', errors='coerce')
    except: return None

# --- 2. LOGIN ---
if 'perfil' not in st.session_state: st.session_state.perfil = None

if st.session_state.perfil is None:
    st.title("🔑 Portal MJ Soluções - Login")
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif u in ["MJ INFINITE CASH D", "VP INFINITE CASH D", "MJ PICPAY CASH D"] and p == "12345":
            st.session_state.perfil = "cliente"; st.session_state.usuario = u
            st.rerun()
        else: st.error("❌ Usuário ou senha incorretos.")
else:
    # --- 3. INTERFACE LOGADA ---
    
    # Define o Menu Lateral
    opcoes = ["🏠 Home", "🛒 Suas vendas"]
    if st.session_state.perfil == "admin":
        opcoes.append("⚙️ Adicionar Taxas")
    opcoes.append("🚪 Sair")

    st.sidebar.title(f"👤 {st.session_state.usuario}")
    
    # Relógio de Sincronização (Informa que o portal está vivo)
    st.sidebar.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border-left: 5px solid #2ecc71;">
            <small>🔄 <b>Sincronizado às:</b> {datetime.now().strftime('%H:%M:%S')}</small>
        </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.divider()
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes)
    
    if menu == "🚪 Sair": 
        st.session_state.perfil = None
        st.rerun()

    # --- 4. ABA: ADICIONAR TAXAS (SÓ ADMIN) ---
    if menu == "⚙️ Adicionar Taxas":
        st.title("➕ Cadastrar Nova Taxa por Cliente")
        st.write("Configuração individual por Maquininha (NS). Digite o valor em porcentagem.")
        
        with st.form("form_taxa", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome_cli = c1.text_input("Nome do Cliente (Igual ao Robô)")
            ns_maquina = c2.text_input("Número de Série (NS)")
            
            c3, c4, c5 = st.columns(3)
            band = c3.selectbox("Bandeira", ["mastercard", "visa", "elo", "amex", "hipercard"])
            meio = c4.text_input("Plano (Ex: em 12x, à vista, débito)")
            
            # Entrada como número inteiro/decimal de porcentagem (Ex: 10.19)
            taxa_input = c5.number_input("Taxa em % (Ex: 10.19)", format="%.2f", step=0.01)
            
            if st.form_submit_button("Gravar no Sistema"):
                if nome_cli and ns_maquina:
                    # Converte a porcentagem para decimal para o banco (ex: 10.19 -> 0.1019)
                    taxa_decimal = taxa_input / 100
                    try:
                        conn.table("taxas_clientes").insert({
                            "cliente": nome_cli.upper().strip(), 
                            "ns": ns_maquina.strip(),
                            "bandeira": band, 
                            "meio": meio.lower().strip(), 
                            "taxa_decimal": taxa_decimal
                        }).execute()
                        st.success(f"✅ Taxa de {taxa_input}% salva para {nome_cli}!")
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco: {e}")
                else:
                    st.warning("⚠️ Preencha Nome e NS obrigatoriamente.")

    # --- 5. ABAS: HOME / VENDAS ---
    else:
        # Atualização automática a cada 30 segundos
        st_autorefresh(interval=30000, key="refresh")
        
        try:
            # Busca os dados da VIEW dashboard_vendas
            df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            
            if not df_v.empty:
                # Limpeza de Segurança (Remove nan e erros de lojista)
                df_v = df_v.dropna(subset=['lojista'])
                df_v = df_v[df_v['lojista'].astype(str).str.lower() != 'nan'].copy()
                df_v = df_v[~df_v['lojista'].str.contains("NÃO", na=False)].copy()

                # Tratamento de Datas
                df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
                df_v = df_v.dropna(subset=['data_dt'])

                # --- FILTROS ---
                if st.session_state.perfil == "admin":
                    st.title("👨‍✈️ Painel Geral MJ")
                    lista_lj = sorted([str(x) for x in df_v['lojista'].unique() if x])
                    escolha = st.sidebar.multiselect("Filtrar Lojistas:", options=lista_lj, default=lista_lj)
                    v_c = df_v[df_v['lojista'].isin(escolha)].copy()
                else:
                    st.title(f"🏠 Painel: {st.session_state.usuario}")
                    v_c = df_v[df_v['lojista'] == st.session_state.usuario].copy()

                # Filtro de Data na Sidebar
                st.sidebar.divider()
                d_ini = st.sidebar.date_input("Início", v_c['data_dt'].min().date() if not v_c.empty else datetime.now().date())
                d_fim = st.sidebar.date_input("Fim", v_c['data_dt'].max().date() if not v_c.empty else datetime.now().date())
                v_c = v_c[(v_c['data_dt'].dt.date >= d_ini) & (v_c['data_dt'].dt.date <= d_fim)]

                # --- MÉTRICAS ---
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}")
                m2.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
                m3.metric("Qtd Vendas", len(v_c))
                if st.session_state.perfil == "admin":
                    m4.metric("Seu Lucro (R$)", f"R$ {v_c['spread_rs'].sum():,.2f}")

                st.write("---")
                # Exibe Tabela formatada
                st.subheader("📋 Relatório de Transações")
                exibir = v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].copy()
                exibir['taxa_cliente'] = (pd.to_numeric(exibir['taxa_cliente'], errors='coerce') * 100).map('{:.2f}%'.format)
                st.dataframe(exibir.sort_index(ascending=False), use_container_width=True)

            else: 
                st.info("Aguardando sincronização dos robôs...")
        except Exception as e: 
            st.error(f"Erro no sistema: {e}")

st.sidebar.caption("MJ Soluções Comercial v5.0")
