import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 1. จัดการฐานข้อมูล (SQLite) ---
DB_NAME = 'finance_v4_deposit.db'

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

# --- 2. หน้าจอแอป (UI) ---
st.set_page_config(page_title="My Finance & Savings", layout="wide")
init_db()
all_df = load_all_data()

st.title("💰 บันทึกรายรับ-รายจ่าย & เงินฝาก _นัท-ยุ้ย")

# --- ส่วนที่ 1: กราฟเปรียบเทียบ (รวมเงินฝากด้วย) ---
if not all_df.empty:
    st.subheader("📈 ภาพรวมรายเดือน")
    summary_df = all_df.groupby(['month_year', 'type'])['amount'].sum().reset_index()
    fig = go.Figure()
    # กำหนดสีตามประเภท
    colors = {"รายรับ": "#2ecc71", "รายจ่าย": "#e74c3c", "เงินฝาก": "#3498db"}
    
    for t in ["รายรับ", "รายจ่าย", "เงินฝาก"]:
        data = summary_df[summary_df['type'] == t]
        fig.add_trace(go.Bar(
            x=data['month_year'], y=data['amount'], name=t,
            marker_color=colors.get(t, "#95a5a6")
        ))
    fig.update_layout(barmode='group', height=350)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- ส่วนที่ 2: เพิ่มข้อมูล (พร้อมช้อยเลือกรายการเดิม) ---
col_add, col_stat = st.columns([1, 1])

with col_add:
    st.subheader("➕ บันทึกรายการ")
    # ดึงชื่อรายการเดิมมาทำเป็น Choice
    existing_items = []
    if not all_df.empty:
        existing_items = sorted(all_df['description'].unique().tolist())
    
    with st.form("add_form", clear_on_submit=True):
        f_date = st.date_input("วันที่", datetime.now())
        
        # ช่องรายการแบบเลือกได้ (Dropdown) หรือพิมพ์เอง (Text Input)
        st.write("ชื่อรายการ (เลือกจากของเดิมหรือพิมพ์ใหม่)")
        f_desc_choice = st.selectbox("เลือกจากรายการที่เคยใช้", ["-- รายการใหม่ --"] + existing_items)
        f_desc_new = st.text_input("หรือพิมพ์รายการใหม่ที่นี่")
        
        # เลือกเอาอันที่พิมพ์ใหม่ถ้ามีการพิมพ์ ถ้าไม่พิมพ์ให้เอาจากที่เลือก
        final_desc = f_desc_new if f_desc_new else (f_desc_choice if f_desc_choice != "-- รายการใหม่ --" else "")
        
        f_type = st.selectbox("ประเภท", ["รายรับ", "รายจ่าย", "เงินฝาก"])
        f_amt = st.number_input("จำนวนเงิน", min_value=0.0, step=50.0)
        
        if st.form_submit_button("✅ บันทึกข้อมูล"):
            if final_desc:
                add_data(f_date, final_desc, f_type, f_amt)
                st.rerun()
            else:
                st.error("กรุณาระบุชื่อรายการ")

with col_stat:
    st.subheader("📊 สรุปยอดรายเดือน")
    if not all_df.empty:
        months_list = sorted(all_df['month_year'].unique(), reverse=True)
        sel_month = st.selectbox("เลือกเดือนที่ต้องการดู", months_list)
        
        m_df = all_df[all_df['month_year'] == sel_month]
        inc = m_df[m_df['type'] == "รายรับ"]['amount'].sum()
        exp = m_df[m_df['type'] == "รายจ่าย"]['amount'].sum()
        sav = m_df[m_df['type'] == "เงินฝาก"]['amount'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("รายรับ", f"{inc:,.2f}")
        c2.metric("รายจ่าย", f"-{exp:,.2f}")
        c3.metric("เงินฝาก", f"{sav:,.2f}")
        c4.metric("คงเหลือสุทธิ", f"{(inc - exp - sav):,.2f}")
    else:
        st.info("ยังไม่มีข้อมูล")

st.divider()

# --- ส่วนที่ 3: จัดการข้อมูล ---
if not all_df.empty:
    st.subheader(f"📑 รายการประจำเดือน {sel_month}")
    for index, row in m_df.iterrows():
        # แสดงแถบสีต่างกันตามประเภท
        color_tag = "🔵" if row['type'] == "เงินฝาก" else ("🟢" if row['type'] == "รายรับ" else "🔴")
        with st.expander(f"{color_tag} {row['date']} | {row['description']} | {row['amount']:,.2f} บาท"):
            with st.form(key=f"edit_{row['id']}"):
                e_date = st.date_input("แก้ไขวันที่", datetime.strptime(row['date'], "%Y-%m-%d"))
                e_desc = st.text_input("แก้ไขรายการ", value=row['description'])
                e_type = st.selectbox("แก้ไขประเภท", ["รายรับ", "รายจ่าย", "เงินฝาก"], 
                                     index=["รายรับ", "รายจ่าย", "เงินฝาก"].index(row['type']))
                e_amt = st.number_input("แก้ไขจำนวนเงิน", value=row['amount'])
                
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 บันทึกการแก้ไข"):
                    update_data(row['id'], e_date, e_desc, e_type, e_amt)
                    st.rerun()
                if b2.form_submit_button("🗑️ ลบรายการ"):
                    delete_data(row['id'])
                    st.rerun()