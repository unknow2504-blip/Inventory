from flask import Flask, render_template_string, request, redirect, send_file
import sqlite3
import pandas as pd
from reportlab.pdfgen import canvas
from io import BytesIO
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

# สร้าง/อัปเดตตารางฐานข้อมูล
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS items 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, unit TEXT, balance INTEGER DEFAULT 0, image_path TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS history 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, amount INTEGER, type TEXT, user_name TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- หน้าแรก: จัดการคลัง ---
@app.route('/')
def index():
    search = request.args.get('search', '')
    conn = get_db_connection()
    if search:
        items = conn.execute("SELECT * FROM items WHERE name LIKE ?", ('%'+search+'%',)).fetchall()
    else:
        items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    
    return render_template_string('''
        <style>
            body { font-family: sans-serif; max-width: 900px; margin: auto; padding: 20px; background: #f4f7f6; }
            .nav { margin-bottom: 20px; padding: 10px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            th { background: #007bff; color: white; }
            .btn-add { background: #28a745; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer; }
        </style>

        <div class="nav">
            <a href="/">🏠 หน้าหลักคลังสินค้า</a> | 
            <a href="/history">📜 ดูประวัติการเบิก-รับ</a>
        </div>

        <h1>📦 ระบบจัดการคลังสินค้า</h1>
        
        <form method="get" style="margin-bottom: 20px;">
            <input name="search" placeholder="ค้นหาชื่ออุปกรณ์..." value="{{ search }}" style="padding:8px; width:250px;">
            <button type="submit" style="padding:8px;">🔍 ค้นหา</button>
        </form>

        <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3>➕ เพิ่มอุปกรณ์ใหม่ (อัปโหลดรูปได้)</h3>
            <form action="/add" method="post" enctype="multipart/form-data" style="display: flex; gap: 10px; flex-wrap: wrap;">
                <input name="name" placeholder="ชื่อของ" required style="padding:8px;">
                <input name="unit" placeholder="หน่วย (ชิ้น/กล่อง)" required style="padding:8px;">
                <input type="file" name="file" accept="image/*" style="padding:5px;">
                <button type="submit" class="btn-add">บันทึกเข้าคลัง</button>
            </form>
        </div>

        <table>
            <tr><th>รูป</th><th>ชื่ออุปกรณ์</th><th>ยอดคงเหลือ</th><th>จัดการ</th></tr>
            {% for item in items %}
            <tr>
                <td style="text-align:center;">
                    {% if item.image_path %}
                        <img src="{{ item.image_path }}" width="60" style="border-radius:4px;">
                    {% else %} ❌ {% endif %}
                </td>
                <td><strong>{{ item.name }}</strong><br><small>หน่วย: {{ item.unit }}</small></td>
                <td style="font-size: 1.2em;">{{ item.balance }}</td>
                <td>
                    <form action="/update" method="post">
                        <input type="hidden" name="id" value="{{ item.id }}">
                        <input name="user_name" placeholder="ชื่อผู้ทำรายการ" required style="width:100px; padding:5px;">
                        <input type="number" name="amount" style="width:50px; padding:5px;" required min="1">
                        <button name="type" value="IN" style="background:#007bff; color:white; border:none; padding:5px 10px;">รับ</button>
                        <button name="type" value="OUT" style="background:#dc3545; color:white; border:none; padding:5px 10px;">เบิก</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    ''', items=items, search=search)

# --- หน้าประวัติ: ดูย้อนหลัง ---
@app.route('/history')
def history():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM history ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template_string('''
        <style>
            body { font-family: sans-serif; max-width: 900px; margin: auto; padding: 20px; background: #f4f7f6; }
            .nav { margin-bottom: 20px; padding: 10px; background: white; border-radius: 8px; }
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            .type-IN { color: green; font-weight: bold; }
            .type-OUT { color: red; font-weight: bold; }
        </style>
        <div class="nav"><a href="/">🏠 กลับหน้าหลัก</a></div>
        <h1>📜 ประวัติการเบิก-รับของ</h1>
        <table>
            <tr><th>วัน-เวลา</th><th>ชื่ออุปกรณ์</th><th>จำนวน</th><th>ประเภท</th><th>ผู้ทำรายการ</th></tr>
            {% for log in logs %}
            <tr>
                <td>{{ log.timestamp }}</td>
                <td>{{ log.item_name }}</td>
                <td>{{ log.amount }}</td>
                <td class="type-{{ log.type }}">{{ "รับเข้า" if log.type == "IN" else "เบิกออก" }}</td>
                <td>{{ log.user_name }}</td>
            </tr>
            {% endfor %}
        </table>
    ''', logs=logs)

@app.route('/add', methods=['POST'])
def add():
    file = request.files.get('file')
    filename = ""
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        filename = "/static/uploads/" + file.filename
    
    conn = get_db_connection()
    conn.execute('INSERT INTO items (name, unit, image_path) VALUES (?, ?, ?)', 
                 (request.form['name'], request.form['unit'], filename))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/update', methods=['POST'])
def update():
    item_id, amount, t_type, user = request.form['id'], int(request.form['amount']), request.form['type'], request.form['user_name']
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if item:
        new_bal = item['balance'] + amount if t_type == 'IN' else item['balance'] - amount
        conn.execute('UPDATE items SET balance = ? WHERE id = ?', (max(0, new_bal), item_id))
        conn.execute('INSERT INTO history (item_name, amount, type, user_name) VALUES (?, ?, ?, ?)',
                     (item['name'], amount, t_type, user))
        conn.commit()
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run()

