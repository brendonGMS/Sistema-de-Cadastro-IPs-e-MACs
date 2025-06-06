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

def importar_dados_df(df):
    inseridos = 0
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
                        inseridos += 1
                    except sqlite3.IntegrityError:
                        continue
        st.success(f"Importação concluída: {inseridos} dispositivo(s) inserido(s).")
    else:
        st.warning("Colunas obrigatórias não encontradas: ip, mac, nome.")

def importar_dados_csv(csv_url):
    try:
        # Tenta ler com vírgula primeiro
        try:
            df = pd.read_csv(csv_url)
        except:
            df = pd.read_csv(csv_url, sep=';')
        importar_dados_df(df)
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

menu = st.sidebar.radio("Menu", ["Cadastrar Dispositivo", "Dispositivos Cadastrados", "Importar Planilha (CSV via link ou arquivo)"])

if menu == "Cadastrar Dispositivo":
    st.subheader("Novo dispositivo")
    name = st.text_input("Nome do dispositivo")
    ip = st.text_input("Endereço IP (ex: 192.168.0.1)")
    mac = st.text_input("Endereço MAC (ex: 00:1A:2B:3C:4D:5E)")
    if st.button("Cadastrar"):
        add_device(ip, mac, name)

elif menu == "Dispositivos Cadastrados":
    st.subheader("Dispositivos Cadastrados")
    devices = view_devices()
    
    search_term = st.text_input("🔍 Filtrar por nome, IP ou MAC", placeholder="Digite para buscar...")
    if search_term:
        search_lower = search_term.lower()
        devices = [
            (name, ip, mac) for (name, ip, mac) in devices 
            if (search_lower in name.lower()) 
            or (search_lower in ip.lower()) 
            or (search_lower in mac.lower())
        ]
    
    if devices:
        # Cria 4 colunas (ajuste os valores conforme necessidade)
        col1, col2, col3, col4 = st.columns([3, 2, 3, 2])
        
        # Cabeçalho
        with col1:
            st.markdown("**Nome**")
        with col2:
            st.markdown("**IP**")
        with col3:
            st.markdown("**MAC**")
        
        st.divider()  # Linha separadora
        
        # Linhas com dispositivos
        for name, ip, mac in devices:
            col1, col2, col3, col4 = st.columns([3, 2, 3, 2])
            
            with col1:
                st.text(name)
            with col2:
                st.text(ip)
            with col3:
                st.text(mac)
            with col4:
                if st.button("Remover", key=f"rm_{ip}", help="Remover dispositivo"):
                    st.session_state['ip_to_remove'] = ip
        
        # Confirmação (aparece apenas se um IP foi selecionado)
        if 'ip_to_remove' in st.session_state:
            st.warning("Tem certeza que deseja remover este dispositivo?")
            
            confirm_col1, confirm_col2, _ = st.columns([1, 1, 4])
            with confirm_col1:
                if st.button("Sim"):
                    with get_db() as conn:
                        conn.execute("DELETE FROM devices WHERE ip_address = ?", (st.session_state['ip_to_remove'],))
                    st.success("Removido!")
                    del st.session_state['ip_to_remove']
                    st.experimental_rerun()
            with confirm_col2:
                if st.button("Não"):
                    del st.session_state['ip_to_remove']
    
    else:
        st.info("Nenhum dispositivo cadastrado ainda.")

elif menu == "Importar Planilha (CSV via link ou arquivo)":
    st.subheader("Importar planilha (CSV)")

    import_type = st.radio("Tipo de importação", ["Arquivo CSV local", "Link de CSV da web"])

    if import_type == "Arquivo CSV local":
        uploaded_file = st.file_uploader("Escolha um arquivo .csv", type=["csv"])
        if uploaded_file is not None:
            try:
                # Tenta com vírgula primeiro
                try:
                    df = pd.read_csv(uploaded_file)
                except:
                    df = pd.read_csv(uploaded_file, sep=';')

                df.columns = [normalize_col_name(col) for col in df.columns]
                st.write("Pré-visualização da planilha:")
                st.dataframe(df.head())

                if all(col in df.columns for col in ['ip', 'mac', 'nome']):
                    if st.button("Importar"):
                        importar_dados_df(df)
                else:
                    st.warning("A planilha deve conter as colunas: ip, mac, nome.")
            except Exception as e:
                st.warning(f"Erro ao ler o arquivo CSV: {e}")

    elif import_type == "Link de CSV da web":
        csv_url = st.text_input("Cole aqui o link direto do CSV (Google Sheets publicado como CSV)")
        if csv_url:
            if st.button("Importar via link"):
                importar_dados_csv(csv_url)

