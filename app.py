import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime, date
import numpy as np

# 1. TENTATIVA DE CONFIGURAÇÃO INICIAL (FORÇADA)
try:
    st.set_page_config(page_title="Portal MJ PAG PRO", layout="wide")
except:
    pass

# --- FUNÇÕES DE SUPORTE ---
def safe_to_numeric(val):
    try:
        return pd.to_numeric(val, errors='coerce')
    except:
        return 0.0

def converter_data_seguro(data_str):
    try:
        if not data_str: return None
        return pd.to_datetime(data_str, errors='coerce')
    except:
        return None

# --- BLOCO PRINCIPAL COM CAPTURA DE ERRO TOTAL ---
try:
    # CONEXÃO
    SUPABASE_URL = "https://oiuyklgtcazbtuvwmelv.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
    
    conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

    if 'perfil' not in st.session_state: st.session_state.perfil = None

    # TELA DE LOGIN SIMPLIFICADA PARA TESTE
    if st.session_state.perfil is None:
        st.title("🔐 Portal MJ PAG PRO")
        u = st.text_input("Usuário").lower().strip()
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if u == "admin" and p == "mj123":
                st.session_state.perfil = "admin"
                st.session_state.usuario = "ADMINISTRADOR"
                st.rerun()
            else:
                res = conn.table("estabelecimentos").select("*").eq("email", u).execute()
                if res.data and p == str(res.data[0].get('senha', '12345')):
                    st.session_state.perfil = "cliente"
                    st.session_state.usuario = res.data[0]['nome_fantasia']
                    st.rerun()
                else:
                    st.error("Credenciais inválidas")
    else:
        # MENU
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Gestão", "Sair"])
        
        if menu == "Sair":
            st.session_state.perfil = None
            st.rerun()

        if menu == "Gestão":
            st.subheader("Gestão de Clientes")
            res = conn.table("estabelecimentos").select("*").execute()
            st.dataframe(pd.DataFrame(res.data))

        if menu == "Dashboard":
            st.title("📊 Dashboard MJ")
            
            # BUSCA DE DADOS
            v_res = conn.table("vendas").select("*").execute()
            m_res = conn.table("maquinas_ns").select("*").execute()
            
            if v_res.data and m_res.data:
                df_v = pd.DataFrame(v_res.data)
                df_m = pd.DataFrame(m_res.data)

                # Tratamento de Nulos para evitar crash
                df_v['bruto'] = df_v['bruto'].apply(safe_to_numeric).fillna(0.0)
                
                # Exibição básica para testar se o erro some
                st.write(f"Total de vendas no banco: {len(df_v)}")
                st.metric("Volume Bruto", f"R$ {df_v['bruto'].sum():,.2f}")
                st.dataframe(df_v.head(20))
            else:
                st.warning("Sem dados para exibir.")

except Exception as e:
    # SE TUDO FALHAR, MOSTRA O ERRO NA TELA EM VEZ DO "OH NO"
    st.error("⚠️ O SISTEMA ENCONTROU UM ERRO TÉCNICO:")
    st.code(str(e))
    st.info("Por favor, tire um print desta tela e envie para análise.")
