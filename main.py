import streamlit as st
import sqlite3
import pandas as pd

conexao = sqlite3.connect("banco.db", check_same_thread=False)
cursor = conexao.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    saldo REAL NOT NULL
)''')

conexao.commit()



st.title("Dashboard sicoob ")

st.subheader("Bem-vindo ao seu dashboard financeiro!")

st.divider()
st.header("Cadastro de Usuário")


Nome = st.text_input("digite seu nome:")
Saldouser = st.number_input("digite seu saldo:", min_value=0.0, step=0.01)

if st.button("Cadastrar"):
    if Nome and Saldouser is not None:
      

        cursor.execute (
        "INSERT INTO users (nome, saldo) VALUES (?, ?)", 
        (Nome, Saldouser)
                        )
    conexao.commit()
    
else:
    st.warning("Por favor, preencha todos os campos.")


conexao.close()
