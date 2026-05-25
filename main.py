import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Dashboard Sicoob", layout="wide")

def create_connection():
    """Cria conexão com o banco de dados"""
    return sqlite3.connect("banco.db", check_same_thread=False)

def create_tables():
    """Cria as tabelas necessárias no banco de dados (recria se estrutura antiga)"""
    conexao = create_connection()
    cursor = conexao.cursor()
    
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if not columns or 'username' not in columns or 'password' not in columns:
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                nome TEXT NOT NULL,
                saldo REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Banco de dados atualizado para nova estrutura com autenticação!")
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                nome TEXT NOT NULL,
                saldo REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    conexao.commit()
    conexao.close()

def make_hashes(password):
    """Cria hash da senha usando SHA-256"""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    """Verifica se a senha corresponde ao hash"""
    if make_hashes(password) == hashed_text:
        return True
    return False

def add_user(username, password, nome, saldo):
    """Adiciona novo usuário ao banco de dados"""
    conexao = create_connection()
    cursor = conexao.cursor()
    
    try:
        hashed_password = make_hashes(password)
        cursor.execute(
            "INSERT INTO users (username, password, nome, saldo) VALUES (?, ?, ?, ?)",
            (username, hashed_password, nome, saldo)
        )
        conexao.commit()
        sucesso = True
        mensagem = "Usuário cadastrado com sucesso!"
    except sqlite3.IntegrityError:
        sucesso = False
        mensagem = "Nome de usuário já existe. Tente outro."
    finally:
        conexao.close()
    
    return sucesso, mensagem

def login_user(username, password):
    """Realiza login do usuário"""
    conexao = create_connection()
    cursor = conexao.cursor()
    
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, make_hashes(password))
    )
    
    data = cursor.fetchall()
    conexao.close()
    
    return data

def get_user_data(username):
    """Obtém dados do usuário logado"""
    conexao = create_connection()
    cursor = conexao.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    data = cursor.fetchone()
    conexao.close()
    
    return data

def update_user_saldo(username, novo_saldo):
    """Atualiza o saldo do usuário"""
    conexao = create_connection()
    cursor = conexao.cursor()
    
    cursor.execute(
        "UPDATE users SET saldo = ? WHERE username = ?",
        (novo_saldo, username)
    )
    
    conexao.commit()
    conexao.close()

create_tables()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'user_data' not in st.session_state:
    st.session_state['user_data'] = None

def logout():
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''
    st.session_state['user_data'] = None
    st.rerun()

def login_screen():
    st.title("🔐 Dashboard Sicoob - Login")
    st.markdown("### Faça login para acessar seu dashboard financeiro")
    
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Cadastro"])
    
    with tab1:
        st.subheader("Acessar Conta")
        login_user_input = st.text_input("Nome de Usuário", key="login_username")
        login_password_input = st.text_input("Senha", type="password", key="login_password")
        
        if st.button("Entrar", type="primary", key="login_button"):
            if login_user_input and login_password_input:
                user_data = login_user(login_user_input, login_password_input)
                if user_data:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_user_input
                    st.session_state['user_data'] = user_data[0]
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos!")
            else:
                st.warning("Preencha todos os campos!")
    
    with tab2:
        st.subheader("Criar Nova Conta")
        novo_username = st.text_input("Escolha um nome de usuário", key="new_username")
        novo_nome = st.text_input("Seu nome completo", key="new_nome")
        novo_password = st.text_input("Crie uma senha", type="password", key="new_password")
        confirm_password = st.text_input("Confirme a senha", type="password", key="confirm_password")
        novo_saldo = st.number_input("Saldo inicial (opcional)", min_value=0.0, step=0.01, value=0.0)
        
        if st.button("Cadastrar", key="register_button"):
            if not novo_username or not novo_nome or not novo_password:
                st.warning("Preencha todos os campos obrigatórios!")
            elif novo_password != confirm_password:
                st.error("As senhas não coincidem!")
            elif len(novo_password) < 4:
                st.error("A senha deve ter pelo menos 4 caracteres!")
            else:
                sucesso, mensagem = add_user(novo_username, novo_password, novo_nome, novo_saldo)
                if sucesso:
                    st.success(mensagem)
                    st.info("Agora você pode fazer login na aba 'Login'")
                else:
                    st.error(mensagem)

def dashboard_screen():
    with st.sidebar:
        st.title("👤 Perfil")
        if st.session_state['user_data']:
            user_id, username, _, nome, saldo, created_at = st.session_state['user_data']
            st.write(f"**Usuário:** {username}")
            st.write(f"**Nome:** {nome}")
            st.write(f"**Saldo:** R$ {saldo:,.2f}")
            st.divider()
            st.info(f"📅 Membro desde: {created_at}")
        
        st.divider()
        if st.button("🚪 Sair / Logout", type="secondary", on_click=logout):
            pass
    
    st.title("📊 Dashboard Sicoob")
    st.subheader(f"Bem-vindo ao seu dashboard financeiro, {st.session_state['user_data'][3] if st.session_state['user_data'] else ''}!")
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    if st.session_state['user_data']:
        user_saldo = st.session_state['user_data'][4]
        col1.metric("Saldo Atual", f"R$ {user_saldo:,.2f}")
        col2.metric("ID do Usuário", st.session_state['user_data'][0])
        col3.metric("Status", "Ativo")
    
    st.divider()
    
    st.header("💰 Operações Financeiras")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Adicionar Saldo")
        valor_deposito = st.number_input(
            "Valor para depósito:", 
            min_value=0.0, 
            step=0.01,
            key="deposito_valor"
        )
        
        if st.button("💵 Depositar", type="primary", key="depositar_btn"):
            if valor_deposito > 0:
                novo_saldo = user_saldo + valor_deposito
                update_user_saldo(st.session_state['username'], novo_saldo)
                st.session_state['user_data'] = get_user_data(st.session_state['username'])
                st.success(f"Depósito de R$ {valor_deposito:,.2f} realizado com sucesso!")
                st.rerun()
    
    with col2:
        st.subheader("Retirar Saldo")
        valor_saque = st.number_input(
            "Valor para saque:", 
            min_value=0.0, 
            step=0.01,
            key="saque_valor"
        )
        
        if st.button("💸 Sacar", type="primary", key="sacar_btn"):
            if valor_saque > 0:
                if valor_saque <= user_saldo:
                    novo_saldo = user_saldo - valor_saque
                    update_user_saldo(st.session_state['username'], novo_saldo)
                    st.session_state['user_data'] = get_user_data(st.session_state['username'])
                    st.success(f"Saque de R$ {valor_saque:,.2f} realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Saldo insuficiente!")
    
    st.divider()
    
    st.header("📋 Informações da Conta")
    
    if st.session_state['user_data']:
        user_info = {
            'ID': st.session_state['user_data'][0],
            'Usuário': st.session_state['user_data'][1],
            'Nome Completo': st.session_state['user_data'][3],
            'Saldo Atual': f"R$ {st.session_state['user_data'][4]:,.2f}",
            'Data de Cadastro': st.session_state['user_data'][5]
        }
        
        st.json(user_info)

def main():
    if st.session_state['logged_in']:
        dashboard_screen()
    else:
        login_screen()

if __name__ == '__main__':
    main()