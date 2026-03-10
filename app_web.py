import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 1. จัดการฐานข้อมูล (SQLite) ---
DB_NAME = 'finance_full_v1.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS finance 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, description TEXT, type TEXT, amount REAL, month_year TEXT)''')
    conn.commit()
    conn.close()

def add_data(date_obj, desc, t_type, amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO finance (date, description, type, amount, month_year) VALUES (?,?,?,?,?)",
              (date_obj.strftime("%Y-%m-%d"), desc, t_type, amount, date_obj.strftime("%m/%Y")))
    conn.commit()
    conn.close()

def update_data(id, date_obj, desc, t_type, amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE finance SET date=?, description=?, type=?, amount=?, month_year=? WHERE id=?",
              (date_obj.strftime("%Y-%m-%d"), desc, t_type, amount, date_obj.strftime("%m/%Y"), id))
    conn.commit()
    conn.close()

def delete_data(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM finance WHERE id=?", (id,))
    conn.commit()
    conn.close()

def load_all_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM finance ORDER BY date DESC", conn)
    conn.close()
    return df

# --- 2. ส่วนหน้าจอแอป (UI) ---
st.set_page_config(page_title="My Finance Dashboard", layout="wide")
init_db()
all_df = load_all_data()

st.title("💰 บันทึกรายรับ-รายจ่าย & Dashboard")

# --- ส่วนที่ 1: กราฟเปรียบเทียบรายเดือน (รูปแบบเดิม) ---
if not all_df.empty:
    st.subheader("📈 กราฟเปรียบเทียบรายรับ-รายจ่ายแต่ละเดือน")
    # รวมข้อมูลเพื่อวาดกราฟ
    summary_df = all_df.groupby(['month_year', 'type'])['amount'].sum().reset_index()
    fig = go.Figure()
    for t in ["รายรับ", "รายจ่าย"]:
        data = summary_df[summary_df['type'] == t]
        fig.add_trace(go.Bar(
            x=data['month_year'], y=data['amount'], name=t,
            marker_color='#2ecc71' if t == "รายรับ" else '#e74c3c'
        ))
    fig.update_layout(barmode='group', height=300, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- ส่วนที่ 2: เพิ่มข้อมูลใหม่ & สรุปยอดเดือนที่เลือก ---
col_add, col_stat = st.columns([1, 1])

with col_add:
    st.subheader("➕ เพิ่มรายการใหม่")
    with st.form("add_form", clear_on_submit=True):
        f_date = st.date_input("วันที่", datetime.now()) # เลือกแบบปฏิทิน
        f_desc = st.text_input("รายการ")
        f_type = st.selectbox("ประเภท", ["รายรับ", "รายจ่าย"])
        f_amt = st.number_input("จำนวนเงิน", min_value=0.0, step=10.0)
        if st.form_submit_button("บันทึกข้อมูล"):
            if f_desc:
                add_data(f_date, f_desc, f_type, f_amt)
                st.rerun()

with col_stat:
    st.subheader("📊 สรุปยอดรายเดือน")
    if not all_df.empty:
        months_list = sorted(all_df['month_year'].unique(), reverse=True)
        sel_month = st.selectbox("เลือกเดือนที่จะดู", months_list)
        
        # กรองข้อมูลเดือนที่เลือก
        m_df = all_df[all_df['month_year'] == sel_month]
        inc = m_df[m_df['type'] == "รายรับ"]['amount'].sum()
        exp = m_df[m_df['type'] == "รายจ่าย"]['amount'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("รายรับ", f"{inc:,.2f}")
        c2.metric("รายจ่าย", f"-{exp:,.2f}")
        c3.metric("คงเหลือ", f"{inc-exp:,.2f}")
    else:
        st.info("ยังไม่มีข้อมูล")

st.divider()

# --- ส่วนที่ 3: ตารางจัดการข้อมูล (แก้ไข/ลบ) ---
if not all_df.empty:
    st.subheader(f"📑 รายการทั้งหมดของเดือน {sel_month}")
    # แสดงตารางพร้อมปุ่มแก้ไขในตัว
    for index, row in m_df.iterrows():
        with st.expander(f"📅 {row['date']} | {row['description']} | {row['amount']:,.2f} ({row['type']})"):
            u_col1, u_col2 = st.columns(2)
            
            # ฟอร์มแก้ไขใน Expander
            with st.form(key=f"edit_form_{row['id']}"):
                edit_date = st.date_input("แก้ไขวันที่", datetime.strptime(row['date'], "%Y-%m-%d"))
                edit_desc = st.text_input("แก้ไขรายการ", value=row['description'])
                edit_type = st.selectbox("แก้ไขประเภท", ["รายรับ", "รายจ่าย"], index=0 if row['type']=="รายรับ" else 1)
                edit_amt = st.number_input("แก้ไขจำนวนเงิน", value=row['amount'])
                
                btn_save, btn_del = st.columns(2)
                if btn_save.form_submit_button("💾 บันทึกการแก้ไข"):
                    update_data(row['id'], edit_date, edit_desc, edit_type, edit_amt)
                    st.rerun()
                if btn_del.form_submit_button("🗑️ ลบรายการนี้"):
                    delete_data(row['id'])
                    st.rerun()