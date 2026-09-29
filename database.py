import streamlit as st
import mysql.connector

def get_connection():
    cfg = st.secrets["mysql"]
    return mysql.connector.connect(
        host=cfg.get("host","localhost"),
        port=int(cfg.get("port",3306)),
        user=cfg.get("user","root"),
        password=cfg["password"],
        database=cfg.get("database","blogsphere")
    )

def query(sql, params=(), fetch=False):
    conn=get_connection()
    cur=conn.cursor(dictionary=True)
    try:
        cur.execute(sql,params)
        result=cur.fetchall() if fetch else None
        if not fetch: conn.commit()
        return result
    finally:
        cur.close()
        conn.close()
