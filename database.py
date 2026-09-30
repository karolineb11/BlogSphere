import streamlit as st
import mysql.connector

def get_connection():
    cfg = st.secrets["mysql"]

    return mysql.connector.connect(
        host=cfg["host"],
        port=int(cfg["port"]),
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )

def query(sql, params=(), fetch=False):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(sql, params)
        result = cur.fetchall() if fetch else None

        if not fetch:
            conn.commit()

        return result

    finally:
        cur.close()
        conn.close()
