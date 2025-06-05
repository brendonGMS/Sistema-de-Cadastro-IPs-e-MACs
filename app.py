import streamlit as st
import sqlite3
import pandas as pd
import ipaddress
import unicodedata
from contextlib import contextmanager

# Funções utilitárias
def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def is_valid_mac(mac):
    return len(mac.split(':')) == 6 and all(len(b) == 2 for b in mac.split(':'))

# Normalização dos nomes das colunas
def normalize_col_name(col_name):
    nfkd = unicodedata.normalize('NFKD', col_name)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)]).strip().lower()

# Conexão com o banco de dados
@contextmanager
def get_db():
    conn = sqlite3.connect("devices.db")
    yield conn
    conn.commit()
    conn.close()

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE,
                mac_address TEXT,
                name TEXT
            )
        """)

def add_device(ip, mac, name):
    if not (is_valid_ip(ip) and is_valid_mac(mac) and name):
        st.warning("Dados inválidos. Verifique IP, MAC e nome.")
        return
    with get_db() as conn:
        try:
            conn.execute("INSERT INTO devices (ip_address, mac_address, name) VALUES (?, ?, ?)", (ip, mac, name))
            st.success("Dispositivo adicionado com sucesso!")
        except sqlite3.IntegrityError:
            st.warning("Este IP já está cadastrado.")

def importar_dados_csv(csv_url):
    try:
        df = pd.read_csv(csv_url)

        # Normaliza as colunas
        df.columns = [normalize_col_name(col) for col in df.columns]

        if all(col in df.columns for col in ['ip', 'mac', 'nome']):
            with get_db() as conn:
                for _, row in df.iterrows():
                    ip = str(row['ip']).strip()
                    mac = str(row['mac']).strip()
                    nome = str(row['nome']).strip()
                    if is_valid_ip(ip) and is_valid_mac(mac) and nome:
                        try:
                            conn.execute(
                                "INSERT INTO devices (ip_address, mac_address, name) VALUES (?, ?, ?)",
                                (ip, mac, nome)
                            )
                        except sqlite3.IntegrityError:
                            continue
            st.success("Planilha importada com sucesso!")
        else:
            st.warning("Colunas obrigatórias não encontradas: ip, mac, nome.")
    except Exception as e:
        st.warning(f"Erro ao importar CSV: {e}")

def view_devices():
    with get_db() as conn:
        result = conn.execute("SELECT name, ip_address, mac_address FROM devices").fetchall()
        return result

# Interface
st.set_page_config(page_title="Cadastro de IPs e MACs", layout="centered")
st.title("Cadastro de IPs e MACs")
init_db()

menu = st.sidebar.radio("Menu", ["Cadastrar Dispositivo", "Dispositivos Cadastrados", "Importar Planilha (CSV via link)"])

if menu == "Cadastrar Dispositivo":
    st.subheader("Novo dispositivo")
    name = st.text_input("Nome do dispositivo")
    ip = st.text_input("Endereço IP (ex: 192.168.0.1)")
    mac = st.text_input("Endereço MAC (ex: 00:1A:2B:3C:4D:5E)")
    if st.button("Cadastrar"):
        add_device(ip, mac, name)

elif menu == "Dispositivos Cadastrados":
    st.subheader("Dispositivos cadastrados")
    devices = view_devices()
    if devices:
        df = pd.DataFrame(devices, columns=["Nome", "IP", "MAC"])
        st.dataframe(df)
    else:
        st.info("Nenhum dispositivo cadastrado ainda.")

elif menu == "Importar Planilha (CSV via link)":
    st.subheader("Importar planilha via link do Google Sheets (formato CSV)")
    csv_url = st.text_input("Cole aqui o link direto do CSV (Google Sheets: Arquivo > Compartilhar > Publicar na web > CSV)")
    if st.button("Importar"):
        importar_dados_csv(csv_url)
