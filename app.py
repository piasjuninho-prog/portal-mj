import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configuração visual profissional
st.set_page_config(page_title="Portal MJ PAG", layout="wide", initial_sidebar_state="expanded")

# --- 1. CONEXÃO ---
SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

# Função para converter data
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
    st.title("🔐 Acesso Portal MJ PAG")
    u = st.text_input("Usuário").upper().strip()
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if u == "ADMIN" and p == "mj123":
            st.session_state.perfil = "admin"; st.session_state.usuario = "ADMINISTRADOR"
            st.rerun()
        elif p == "12345":
            st.session_state.perfil = "cliente"; st.session_state.usuario = u
            st.rerun()
        else: st.error("❌ Usuário ou senha incorretos.")
else:
    # --- 3. MENU LATERAL ---
    opcoes_menu = ["🏠 Dashboard", "📂 Criar Planos", "👤 Vincular Cliente", "🚪 Sair"]
    st.sidebar.title(f"👤 {st.session_state.usuario}")
    
    # Relógio de atualização
    st.sidebar.markdown(f"""<div style="background:#f0f2f6;padding:10px;border-radius:5px;border-left:5px solid #2ecc71;">
        <small>🔄 <b>Sincronizado:</b> {datetime.now().strftime('%H:%M:%S')}</small></div>""", unsafe_allow_html=True)
    
    menu = st.sidebar.radio("NAVEGAÇÃO", opcoes_menu)
    if menu == "🚪 Sair": st.session_state.perfil = None; st.rerun()

    # --- 4. ABA: CRIAR PLANOS (ESTILO MJ PAG) ---
    if menu == "📂 Criar Planos" and st.session_state.perfil == "admin":
        st.title("📑 Criando Novo Plano Comercial")
        st.write("Preencha a tabela abaixo com as taxas em % para cada modalidade.")
        
        nome_plano = st.text_input("Nome do Plano", placeholder="Ex: PLANO BLACK D+1")
        
        # Estrutura completa de taxas
        modalidades = ["débito", "à vista", "em 2x", "em 3x", "em 4x", "em 5x", "em 6x", "em 7x", "em 8x", "em 9x", "em 10x", "em 11x", "em 12x"]
        dados_vazios = {
            "Modalidade": modalidades,
            "Mastercard (%)": [0.0] * 13,
            "Visa (%)": [0.0] * 13,
            "Elo (%)": [0.0] * 13,
            "Amex (%)": [0.0] * 13,
            "Hipercard (%)": [0.0] * 13
        }
        df_setup = pd.DataFrame(dados_vazios)

        st.subheader("Configuração de Taxas")
        df_editado = st.data_editor(df_setup, use_container_width=True, hide_index=True)

        if st.button("🚀 SALVAR PLANO COMPLETO NO BANCO", use_container_width=True):
            if nome_plano:
                try:
                    # 1. Salva o nome do plano
                    res = conn.table("planos_mj").insert({"nome_plano": nome_plano.upper()}).execute()
                    id_plano = res.data[0]['id']
                    
                    # 2. Processa todas as colunas de bandeiras
                    taxas_batch = []
                    bandeiras_map = {
                        "Mastercard (%)": "mastercard",
                        "Visa (%)": "visa",
                        "Elo (%)": "elo",
                        "Amex (%)": "amex",
                        "Hipercard (%)": "hipercard"
                    }

                    for _, row in df_editado.iterrows():
                        mod = row['Modalidade']
                        for col_nome, band_ref in bandeiras_map.items():
                            taxas_batch.append({
                                "id_plano": id_plano, 
                                "bandeira": band_ref, 
                                "meio": mod, 
                                "taxa_decimal": row[col_nome]/100
                            })
                    
                    # Salva todas as taxas do plano
                    conn.table("taxas_dos_planos").insert(taxas_batch).execute()
                    st.success(f"✅ Plano '{nome_plano}' criado com sucesso para todas as bandeiras!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("⚠️ Digite um nome para o plano.")

    # --- 5. ABA: VINCULAR CLIENTE ---
    elif menu == "👤 Vincular Cliente" and st.session_state.perfil == "admin":
        st.title("👤 Associar Cliente a um Plano")
        
        # Busca planos cadastrados
        res_p = conn.table("planos_mj").select("id, nome_plano").execute()
        dict_planos = {p['nome_plano']: p['id'] for p in res_p.data}
        
        with st.form("form_vinculo"):
            nome_cliente = st.text_input("Nome do Cliente (Igual ao Robô)")
            ns_cliente = st.text_input("NS da Maquininha (PB1F...)")
            plano_selecionado = st.selectbox("Selecione o Plano de Taxas", options=list(dict_planos.keys()))
            
            if st.form_submit_button("✅ VINCULAR E CONFIGURAR TAXAS", use_container_width=True):
                if nome_cliente and ns_cliente:
                    try:
                        id_p = dict_planos[plano_selecionado]
                        # Busca todas as taxas do plano escolhido
                        res_t = conn.table("taxas_dos_planos").select("*").eq("id_plano", id_p).execute()
                        
                        novas_taxas = []
                        for t in res_t.data:
                            novas_taxas.append({
                                "cliente": nome_cliente.upper().strip(), "ns": ns_cliente.strip(),
                                "bandeira": t['bandeira'], "meio": t['meio'], "taxa_decimal": t['taxa_decimal']
                            })
                        
                        # Insere na tabela que o Dashboard e Robô consultam
                        conn.table("taxas_clientes").insert(novas_taxas).execute()
                        st.success(f"🚀 Cliente {nome_cliente} vinculado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao vincular: {e}")
                else: st.warning("Preencha Nome e NS.")

    # --- 6. ABA: DASHBOARD ---
    elif menu in ["🏠 Dashboard"]:
        st_autorefresh(interval=30000, key="refresh")
        try:
            # Busca os dados da VIEW dashboard_vendas
            df_v = pd.DataFrame(conn.table("dashboard_vendas").select("*").execute().data)
            
            if not df_v.empty:
                # Limpeza
                df_v = df_v[df_v['lojista'].notna() & (df_v['lojista'].astype(str).str.lower() != 'nan')].copy()
                df_v['data_dt'] = df_v['data_venda'].apply(converter_data)
                df_v = df_v.dropna(subset=['data_dt'])

                if st.session_state.perfil == "admin":
                    st.title("👨‍✈️ Painel Geral MJ")
                    lista_lj = sorted(df_v['lojista'].unique())
                    escolha = st.sidebar.multiselect("Filtrar Lojistas:", options=lista_lj, default=lista_lj)
                    v_c = df_v[df_v['lojista'].isin(escolha)].copy()
                else:
                    st.title(f"🏠 Painel: {st.session_state.usuario}")
                    v_c = df_v[df_v['lojista'] == st.session_state.usuario].copy()

                # Filtros de data
                st.sidebar.divider()
                d_ini = st.sidebar.date_input("Início", v_c['data_dt'].min().date() if not v_c.empty else datetime.now().date())
                d_fim = st.sidebar.date_input("Fim", v_c['data_dt'].max().date() if not v_c.empty else datetime.now().date())
                v_c = v_c[(v_c['data_dt'].dt.date >= d_ini) & (v_c['data_dt'].dt.date <= d_fim)]

                # Métricas
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Bruto Total", f"R$ {v_c['bruto'].sum():,.2f}")
                m2.metric("Líquido Esperado", f"R$ {v_c['liquido_cliente'].sum():,.2f}")
                m3.metric("Qtd Vendas", len(v_c))
                if st.session_state.perfil == "admin":
                    m4.metric("Seu Lucro (R$)", f"R$ {v_c['spread_rs'].sum():,.2f}")

                st.write("---")
                # Exibe Tabela formatada
                st.subheader("📋 Últimas Transações")
                exibir = v_c[['data_venda', 'lojista', 'bandeira', 'plano', 'bruto', 'taxa_cliente', 'liquido_cliente']].copy()
                exibir['taxa_cliente'] = (pd.to_numeric(exibir['taxa_cliente'], errors='coerce') * 100).map('{:.2f}%'.format)
                st.dataframe(exibir.sort_index(ascending=False), use_container_width=True)
            else: st.info("Aguardando novas vendas sincronizadas...")
        except Exception as e: st.error(f"Erro no Dashboard: {e}")

st.sidebar.caption("MJ Soluções Comercial v8.0")
