import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Dashboard Sicoob", layout="wide")

def create_connection():
    return sqlite3.connect("banco.db", check_same_thread=False)

def create_tables():
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
        print("Banco de dados atualizado para nova estrutura com autenticacao!")
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_origem_id INTEGER NOT NULL,
            usuario_destino_id INTEGER NOT NULL,
            valor REAL NOT NULL,
            data_transacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_origem_id) REFERENCES users(id),
            FOREIGN KEY (usuario_destino_id) REFERENCES users(id)
        )
    ''')
    
    conexao.commit()
    conexao.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

def add_user(username, password, nome, saldo):
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
        mensagem = "Usuario cadastrado com sucesso!"
    except sqlite3.IntegrityError:
        sucesso = False
        mensagem = "Nome de usuario ja existe. Tente outro."
    finally:
        conexao.close()
    
    return sucesso, mensagem

def login_user(username, password):
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
    conexao = create_connection()
    cursor = conexao.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    data = cursor.fetchone()
    conexao.close()
    
    return data

def get_user_by_username(username):
    conexao = create_connection()
    cursor = conexao.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    data = cursor.fetchone()
    conexao.close()
    
    return data

def update_user_saldo(username, novo_saldo):
    conexao = create_connection()
    cursor = conexao.cursor()
    
    cursor.execute(
        "UPDATE users SET saldo = ? WHERE username = ?",
        (novo_saldo, username)
    )
    
    conexao.commit()
    conexao.close()

def transferir_saldo(username_origem, username_destino, valor):
    conexao = create_connection()
    cursor = conexao.cursor()
    
    try:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username_origem,))
        usuario_origem = cursor.fetchone()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username_destino,))
        usuario_destino = cursor.fetchone()
        
        if not usuario_origem or not usuario_destino:
            return False, "Usuario de origem ou destino nao existe!"
        
        if usuario_origem[0] == usuario_destino[0]:
            return False, "Nao e possivel transferir para si mesmo!"
        
        if usuario_origem[4] < valor:
            return False, "Saldo insuficiente!"
        
        if valor <= 0:
            return False, "O valor deve ser maior que zero!"
        
        novo_saldo_origem = usuario_origem[4] - valor
        novo_saldo_destino = usuario_destino[4] + valor
        
        cursor.execute("UPDATE users SET saldo = ? WHERE id = ?", 
                      (novo_saldo_origem, usuario_origem[0]))
        cursor.execute("UPDATE users SET saldo = ? WHERE id = ?", 
                      (novo_saldo_destino, usuario_destino[0]))
        
        cursor.execute('''
            INSERT INTO transacoes (usuario_origem_id, usuario_destino_id, valor)
            VALUES (?, ?, ?)
        ''', (usuario_origem[0], usuario_destino[0], valor))
        
        conexao.commit()
        return True, f"Transferencia de R$ {valor:,.2f} realizada com sucesso!"
        
    except Exception as e:
        conexao.rollback()
        return False, f"Erro na transferencia: {str(e)}"
    finally:
        conexao.close()

def get_transacoes_usuario(user_id):
    conexao = create_connection()
    cursor = conexao.cursor()
    
    cursor.execute('''
        SELECT t.*, u1.username as origem_username, u2.username as destino_username
        FROM transacoes t
        JOIN users u1 ON t.usuario_origem_id = u1.id
        JOIN users u2 ON t.usuario_destino_id = u2.id
        WHERE t.usuario_origem_id = ? OR t.usuario_destino_id = ?
        ORDER BY t.data_transacao DESC
    ''', (user_id, user_id))
    
    transacoes = cursor.fetchall()
    conexao.close()
    
    return transacoes

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
    st.title("Dashboard Sicoob - Login")
    st.markdown("### Faca login para acessar seu dashboard financeiro")
    
    tab1, tab2 = st.tabs(["Login", "Cadastro"])
    
    with tab1:
        st.subheader("Acessar Conta")
        login_user_input = st.text_input("Nome de Usuario", key="login_username")
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
                    st.error("Usuario ou senha incorretos!")
            else:
                st.warning("Preencha todos os campos!")
    
    with tab2:
        st.subheader("Criar Nova Conta")
        novo_username = st.text_input("Escolha um nome de usuario", key="new_username")
        novo_nome = st.text_input("Seu nome completo", key="new_nome")
        novo_password = st.text_input("Crie uma senha", type="password", key="new_password")
        confirm_password = st.text_input("Confirme a senha", type="password", key="confirm_password")
        novo_saldo = st.number_input("Saldo inicial (opcional)", min_value=0.0, step=0.01, value=0.0)
        
        if st.button("Cadastrar", key="register_button"):
            if not novo_username or not novo_nome or not novo_password:
                st.warning("Preencha todos os campos obrigatorios!")
            elif novo_password != confirm_password:
                st.error("As senhas nao coincidem!")
            elif len(novo_password) < 4:
                st.error("A senha deve ter pelo menos 4 caracteres!")
            else:
                sucesso, mensagem = add_user(novo_username, novo_password, novo_nome, novo_saldo)
                if sucesso:
                    st.success(mensagem)
                    st.info("Agora voce pode fazer login na aba 'Login'")
                else:
                    st.error(mensagem)

def dashboard_screen():
    with st.sidebar:
        st.title("Perfil")
        if st.session_state['user_data']:
            user_id, username, _, nome, saldo, created_at = st.session_state['user_data']
            st.write(f"**Usuario:** {username}")
            st.write(f"**Nome:** {nome}")
            st.write(f"**Saldo:** R$ {saldo:,.2f}")
            st.divider()
            st.info(f"Membro desde: {created_at}")
        
        st.divider()
        if st.button("Sair / Logout", type="secondary", on_click=logout):
            pass
    
    st.title("Dashboard Sicoob")
    st.subheader(f"Bem-vindo ao seu dashboard financeiro, {st.session_state['user_data'][3] if st.session_state['user_data'] else ''}!")
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    if st.session_state['user_data']:
        user_saldo = st.session_state['user_data'][4]
        col1.metric("Saldo Atual", f"R$ {user_saldo:,.2f}")
        col2.metric("ID do Usuario", st.session_state['user_data'][0])
        col3.metric("Status", "Ativo")
    
    st.divider()
    
    st.header("Operacoes Financeiras")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Adicionar Saldo")
        valor_deposito = st.number_input(
            "Valor para deposito:", 
            min_value=0.0, 
            step=0.01,
            key="deposito_valor"
        )
        
        if st.button("Depositar", type="primary", key="depositar_btn"):
            if valor_deposito > 0:
                novo_saldo = user_saldo + valor_deposito
                update_user_saldo(st.session_state['username'], novo_saldo)
                st.session_state['user_data'] = get_user_data(st.session_state['username'])
                st.success(f"Deposito de R$ {valor_deposito:,.2f} realizado com sucesso!")
                st.rerun()
    
    with col2:
        st.subheader("Retirar Saldo")
        valor_saque = st.number_input(
            "Valor para saque:", 
            min_value=0.0, 
            step=0.01,
            key="saque_valor"
        )
        
        if st.button("Sacar", type="primary", key="sacar_btn"):
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
    st.subheader("Transferir Saldo")
    
    col3, col4 = st.columns(2)
    
    with col3:
        username_destino = st.text_input(
            "Username do destinatario:",
            key="transfer_destino"
        )
    
    with col4:
        valor_transferencia = st.number_input(
            "Valor da transferencia:",
            min_value=0.01,
            step=0.01,
            key="transfer_valor"
        )
    
    if st.button("Transferir", type="primary", key="transferir_btn"):
        if username_destino and valor_transferencia > 0:
            sucesso, mensagem = transferir_saldo(
                st.session_state['username'],
                username_destino,
                valor_transferencia
            )
            if sucesso:
                st.success(mensagem)
                st.session_state['user_data'] = get_user_data(st.session_state['username'])
                st.rerun()
            else:
                st.error(mensagem)
        else:
            st.warning("Preencha todos os campos!")
    
    st.divider()
    
    st.header("Informacoes da Conta")
    
    if st.session_state['user_data']:
        user_id = st.session_state['user_data'][0]
        username = st.session_state['user_data'][1]
        nome = st.session_state['user_data'][3]
        saldo = st.session_state['user_data'][4]
        created_at = st.session_state['user_data'][5]
        
        try:
            data_cadastro = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S.%f") if "." in str(created_at) else datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            data_formatada = data_cadastro.strftime("%d/%m/%Y as %H:%M")
        except:
            data_formatada = created_at
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 10px;'>
                    <h4 style='margin: 0; color: #666; font-size: 14px;'>ID do Usuario</h4>
                    <p style='margin: 5px 0 0 0; font-size: 24px; font-weight: bold; color: #1f77b4;'>{user_id}</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #ff7b00; margin-bottom: 10px;'>
                    <h4 style='margin: 0; color: #666; font-size: 14px;'>Nome de Usuario</h4>
                    <p style='margin: 5px 0 0 0; font-size: 24px; font-weight: bold; color: #ff7b00;'>{username}</p>
                </div>
            """, unsafe_allow_html=True)
        
        col3, col4 = st.columns([3, 1])
        with col3:
            st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #2ca02c; margin-bottom: 10px;'>
                    <h4 style='margin: 0; color: #666; font-size: 14px;'>Nome Completo</h4>
                    <p style='margin: 5px 0 0 0; font-size: 24px; font-weight: bold; color: #2ca02c;'>{nome}</p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; margin: 20px 0; text-align: center; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);'>
                <h4 style='margin: 0; color: rgba(255,255,255,0.9); font-size: 18px;'>Saldo Atual</h4>
                <p style='margin: 10px 0 0 0; font-size: 48px; font-weight: bold; color: #ffffff;'>R$ {saldo:,.2f}</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #d62728; margin-bottom: 10px;'>
                <h4 style='margin: 0; color: #666; font-size: 14px;'>Data de Cadastro</h4>
                <p style='margin: 5px 0 0 0; font-size: 20px; font-weight: bold; color: #d62728;'>{data_formatada}</p>
                <p style='margin: 5px 0 0 0; font-size: 14px; color: #888;'>Membro desde {data_formatada}</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        st.header("Historico de Transferencias")
        
        transacoes = get_transacoes_usuario(user_id)
        
        if transacoes:
            transacoes_df = pd.DataFrame(transacoes, 
                                        columns=['id', 'usuario_origem_id', 'usuario_destino_id', 
                                               'valor', 'data_transacao', 'origem_username', 'destino_username'])
            
            for _, transacao in transacoes_df.iterrows():
                tipo = "Enviada" if transacao['usuario_origem_id'] == user_id else "Recebida"
                cor = "#dc3545" if tipo == "Enviada" else "#28a745"
                sinal = "-" if tipo == "Enviada" else "+"
                
                try:
                    data_formatada = datetime.strptime(str(transacao['data_transacao']), 
                                                      "%Y-%m-%d %H:%M:%S.%f").strftime("%d/%m/%Y %H:%M")
                except:
                    data_formatada = str(transacao['data_transacao'])[:19]
                
                st.markdown(f"""
                    <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid {cor}; margin-bottom: 10px;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <div>
                                <span style='font-weight: bold; color: {cor};'>{tipo}</span>
                                <span style='margin: 0 10px; color: #666;'>|</span>
                                <span style='color: #666;'>{data_formatada}</span>
                            </div>
                            <div style='font-weight: bold; font-size: 18px; color: {cor};'>
                                {sinal}R$ {transacao['valor']:,.2f}
                            </div>
                        </div>
                        <div style='margin-top: 5px; color: #888; font-size: 14px;'>
                            {transacao['origem_username']} -> {transacao['destino_username']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Nenhuma transferencia realizada ainda.")

def main():
    if st.session_state['logged_in']:
        dashboard_screen()
    else:
        login_screen()

if __name__ == '__main__':
    main()