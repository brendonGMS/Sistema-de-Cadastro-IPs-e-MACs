import streamlit as st
import sqlite3
import ipaddress
import re
import pandas as pd
import time

# Banco de dados
def get_db():
    conn = sqlite3.connect('devices.db', isolation_level='IMMEDIATE', check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# Inicializar banco
def init_db():
    with get_db() as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT UNIQUE NOT NULL,
            mac_address TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

# Validação
def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def is_valid_mac(mac):
    return bool(re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", mac))

# Inicializa banco
init_db()
st.title("📋 Sistema de Cadastro IP/MAC")

# Reseta os campos após cadastro
if st.session_state.get("cadastro_feito"):
    st.session_state.clear() 

# ------------------------ Cadastro ------------------------ #
with st.expander("➕ Cadastrar Novo Dispositivo", expanded=True):
    with st.form("cadastro_form"):
        ip = st.text_input("Endereço IP:", key="ip_input", value=st.session_state.get("ip_input", ""))
        mac = st.text_input("Endereço MAC (formato 00:1A:2B:3C:4D:5E):", key="mac_input", value=st.session_state.get("mac_input", ""))
        name = st.text_input("Nome do Dispositivo/Pessoa:", key="name_input", value=st.session_state.get("name_input", ""))
        
        if st.form_submit_button("Cadastrar"):
            if not all([ip, mac, name]):
                st.error("Todos os campos são obrigatórios!")
            elif not is_valid_ip(ip):
                st.error("Endereço IP inválido!")
            elif not is_valid_mac(mac):
                st.error("Formato MAC inválido! Use 00:1A:2B:3C:4D:5E")
            else:
                try:
                    with get_db() as conn:
                        conn.execute(
                            "INSERT INTO devices (ip_address, mac_address, name) VALUES (?, ?, ?)",
                            (ip, mac, name)
                        )
                    st.toast(f"{name} cadastrado com sucesso!", icon="✅")
                    
                    # Limpar campos manualmente
                    st.session_state["ip_input"] = ""
                    st.session_state["mac_input"] = ""
                    st.session_state["name_input"] = ""
                    
                    # Mostrar mensagem temporária
                    msg = st.empty()
                    msg.success(f"✅ {name} cadastrado com sucesso!")
                    time.sleep(3)
                    msg.empty()

                except sqlite3.IntegrityError:
                    st.error("IP ou MAC já cadastrado!")



# ------------------------ Gerenciamento ------------------------ #
st.markdown("---")
st.subheader("🔍 Gerenciar Dispositivos")

search_term = st.text_input("Pesquisar por IP, MAC ou Nome:", key="search")

query = """
    SELECT id, ip_address, mac_address, name 
    FROM devices
"""
params = ()

if search_term:
    query += " WHERE ip_address LIKE ? OR mac_address LIKE ? OR name LIKE ?"
    params = (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%")

with get_db() as conn:
    devices = conn.execute(query, params).fetchall()

if search_term and devices:
    df = pd.DataFrame(devices, columns=["ID", "IP", "MAC", "Nome"])
    st.dataframe(df.drop("ID", axis=1), use_container_width=True, hide_index=True)

    for device in devices:
        with st.expander(f"Editar ou Remover — {device[3]}"):
            nome_edit = st.text_input("Nome", value=device[3], key=f"nome_{device[0]}")
            ip_edit = st.text_input("IP", value=device[1], key=f"ip_{device[0]}")
            mac_edit = st.text_input("MAC", value=device[2], key=f"mac_{device[0]}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Atualizar", key=f"update_{device[0]}"):
                    if not all([ip_edit, mac_edit, nome_edit]):
                        st.warning("⚠️ Todos os campos são obrigatórios.")
                    elif not is_valid_ip(ip_edit):
                        st.warning("⚠️ IP inválido.")
                    elif not is_valid_mac(mac_edit):
                        st.warning("⚠️ MAC inválido. Use o formato 00:1A:2B:3C:4D:5E")
                    else:
                        try:
                            with get_db() as conn:
                                conn.execute(
                                    "UPDATE devices SET ip_address = ?, mac_address = ?, name = ? WHERE id = ?",
                                    (ip_edit, mac_edit, nome_edit, device[0])
                                )
                            st.success("✅ Dispositivo atualizado com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("⛔ IP ou MAC já cadastrado em outro dispositivo.")

            with col2:
                if st.button("Remover", key=f"delete_{device[0]}"):
                    with get_db() as conn:
                        conn.execute("DELETE FROM devices WHERE id = ?", (device[0],))
                    st.success(f"✅ Dispositivo `{device[3]}` removido com sucesso!")
                    time.sleep(1)
                    st.rerun()

elif search_term:
    st.info("🔎 Nenhum dispositivo encontrado com esses critérios.")


# ------------------------ Visualização Completa ------------------------ #
st.markdown("---")
st.subheader("📑 Ver Dispositivos Cadastrados")

mostrar = st.checkbox("📂 Mostrar todos os dispositivos cadastrados")

if mostrar:
    with get_db() as conn:
        all_devices = conn.execute("""
            SELECT id, ip_address, mac_address, name, created_at 
            FROM devices ORDER BY created_at DESC
        """).fetchall()

    if all_devices:
        for device in all_devices:
            with st.expander(f"🖥️ {device[3]}"):
                st.markdown(f"""
                - **Nome:** `{device[3]}`
                - **IP:** `{device[1]}`
                - **MAC:** `{device[2]}`
                - **Data de Cadastro:** `{device[4]}`
                """)
                if st.button(f"Remover", key=f"del_full_{device[0]}"):
                    with get_db() as conn:
                        conn.execute("DELETE FROM devices WHERE id = ?", (device[0],))
                    st.success(f"✅ Dispositivo `{device[3]}` removido com sucesso!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("Nenhum dispositivo cadastrado ainda.")
