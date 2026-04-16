import streamlit as st

# 1. Configuração básica
st.set_page_config(page_title="MJ", layout="centered")

# 2. Estado de login simples
if "entrou" not in st.session_state:
    st.session_state.entrou = False

# 3. Lógica de exibição
if not st.session_state.entrou:
    st.header("🔑 Acesso MJ")
    
    # Inputs simples (sem formulário para evitar travas)
    usuario = st.text_input("Digite o usuário", key="user_input")
    senha = st.text_input("Digite a senha", type="password", key="pass_input")
    
    if st.button("ENTRAR AGORA", use_container_width=True):
        if usuario == "admin" and senha == "admin123":
            st.session_state.entrou = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
else:
    st.title("✅ VOCÊ ESTÁ LOGADO!")
    st.balloons()
    if st.button("Sair"):
        st.session_state.entrou = False
        st.rerun()
