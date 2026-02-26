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
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1000px; margin: auto; padding: 20px; background: #f0f2f5; }
            .nav { margin-bottom: 20px; padding: 15px; background: white; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; gap: 20px; font-weight: bold; }
            .nav a { text-decoration: none; color: #007bff; }
            
            .form-container { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 30px; border-top: 5px solid #28a745; }
            .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
            
            table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            th, td { padding: 15px; border-bottom: 1px solid #eee; text-align: left; }
            th { background: #007bff; color: white; }
            
            input, select, button { padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            .btn-save { background: #28a745; color: white; border: none; cursor: pointer; font-weight: bold; width: 100%; margin-top: 10px; }
            .btn-search { background: #007bff; color: white; border: none; cursor: pointer; }
        </style>

        <div class="nav">
            <a href="/">🏠 หน้าหลักจัดการคลัง</a>
            <a href="/history">📜 ดูประวัติการเบิก-รับของ</a>
        </div>

        <h1>📦 ระบบบริหารจัดการคลังสินค้า</h1>

        <div class="form-container">
            <h3 style="margin-top:0; color:#28a745;">➕ เพิ่มรายการอุปกรณ์ใหม่ลงคลัง</h3>
            <form action="/add" method="post" enctype="multipart/form-data">
                <div class="form-grid">
                    <div>
                        <label>ชื่ออุปกรณ์:</label><br>
                        <input name="name" placeholder="ระบุชื่อสิ่งของ" required style="width:100%">
                    </div>
                    <div>
                        <label>หน่วยนับ:</label><br>
                        <input name="unit" placeholder="เช่น ชิ้น, ตัว, กล่อง" required style="width:100%">
                    </div>
                    <div>
                        <label>รูปภาพ (ถ้ามี):</label><br>
                        <input type="file" name="file" accept="image/*" style="width:100%">
                    </div>
                </div>
                <button type="submit" class="btn-save">✅ บันทึกอุปกรณ์ใหม่เข้าสู่ระบบ</button>
            </form>
        </div>

        <div style="margin-bottom: 15px; display: flex; gap: 10px;">
            <form method="get" style="display: flex; gap: 10px; flex-grow: 1;">
                <input name="search" placeholder="พิมพ์ชื่อเพื่อค้นหาของในคลัง..." value="{{ search }}" style="flex-grow: 1;">
                <button type="submit" class="btn-search">🔍 ค้นหา</button>
            </form>
        </div>

        <table>
            <tr>
                <th>รูป</th>
                <th>รายละเอียดอุปกรณ์</th>
                <th>คงเหลือ</th>
                <th style="width: 300px;">จัดการ (รับเข้า/เบิกออก)</th>
            </tr>
            {% for item in items %}
            <tr>
                <td style="text-align:center;">
                    {% if item.image_path %}
                        <img src="{{ item.image_path }}" width="65" height="65" style="object-fit: cover; border-radius: 5px; border: 1px solid #ddd;">
                    {% else %}
                        <span style="color:#ccc; font-size: 12px;">ไม่มีรูป</span>
                    {% endif %}
                </td>
                <td>
                    <strong>{{ item.name }}</strong><br>
                    <small style="color:#666;">หน่วย: {{ item.unit }}</small>
                </td>
                <td style="font-size: 1.3em; color: #007bff;">{{ item.balance }}</td>
                <td>
                    <form action="/update" method="post" style="display: flex; flex-direction: column; gap: 5px;">
                        <input type="hidden" name="id" value="{{ item.id }}">
                        <input name="user_name" placeholder="ชื่อผู้ทำรายการ" required>
                        <div style="display: flex; gap: 5px;">
                            <input type="number" name="amount" placeholder="จำนวน" required min="1" style="flex-grow: 1;">
                            <button name="type" value="IN" style="background:#28a745; color:white; border:none; padding: 8px 15px; border-radius: 5px; cursor:pointer;">รับ</button>
                            <button name="type" value="OUT" style="background:#dc3545; color:white; border:none; padding: 8px 15px; border-radius: 5px; cursor:pointer;">เบิก</button>
                        </div>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    ''', items=items, search=search)

# --- หน้าประวัติ: ดูย้อนหลัง + กรองข้อมูล ---
@app.route('/history')
def history():
    filter_type = request.args.get('type', '')
    search = request.args.get('search', '')
    query = "SELECT * FROM history WHERE 1=1"
    params = []
    if filter_type:
        query += " AND type = ?"; params.append(filter_type)
    if search:
        query += " AND item_name LIKE ?"; params.append('%'+search+'%')
    query += " ORDER BY timestamp DESC"
    
    conn = get_db_connection()
    logs = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template_string('''
        <style>
            body { font-family: sans-serif; max-width: 1000px; margin: auto; padding: 20px; background: #f0f2f5; }
            .nav { margin-bottom: 20px; padding: 15px; background: white; border-radius: 10px; display: flex; gap: 20px; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }
            .filter-bar { background: white; padding: 20px; border-radius: 10px; margin-bottom: 15px; display: flex; gap: 10px; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        </style>
        <div class="nav"><a href="/">🏠 กลับหน้าหลัก</a></div>
        <h1>📜 ประวัติการเคลื่อนไหวอุปกรณ์</h1>
        
        <form method="get" class="filter-bar">
            <strong>กรองข้อมูล:</strong>
            <input name="search" placeholder="ค้นหาชื่อของ..." value="{{ search }}">
            <select name="type">
                <option value="">-- ทุกประเภท --</option>
                <option value="IN" {% if filter_type == 'IN' %}selected{% endif %}>รับเข้า</option>
                <option value="OUT" {% if filter_type == 'OUT' %}selected{% endif %}>เบิกออก</option>
            </select>
            <button type="submit">กรอง</button>
            <a href="/history" style="font-size: 12px; color: #666;">ล้างค่า</a>
            
            <div style="margin-left: auto;">
                <a href="/export/excel" style="background: #1d6f42; color:white; padding: 8px 12px; text-decoration: none; border-radius: 5px;">Excel</a>
                <a href="/export/pdf" style="background: #c1311b; color:white; padding: 8px 12px; text-decoration: none; border-radius: 5px;">PDF</a>
            </div>
        </form>

        <table>
            <tr><th>วัน-เวลา</th><th>ชื่ออุปกรณ์</th><th>จำนวน</th><th>สถานะ</th><th>ผู้ทำรายการ</th></tr>
            {% for log in logs %}
            <tr>
                <td style="color:#666; font-size: 0.9em;">{{ log.timestamp }}</td>
                <td><strong>{{ log.item_name }}</strong></td>
                <td>{{ log.amount }}</td>
                <td style="color: {{ 'green' if log.type == 'IN' else 'red' }}; font-weight: bold;">
                    {{ "✅ รับเข้า" if log.type == "IN" else "📤 เบิกออก" }}
                </td>
                <td>{{ log.user_name }}</td>
            </tr>
            {% endfor %}
        </table>
    ''', logs=logs, filter_type=filter_type, search=search)

# --- ส่วน Export (Excel/PDF) ---
@app.route('/export/excel')
def export_excel():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT timestamp, item_name, amount, type, user_name FROM history", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="inventory_history.xlsx", as_attachment=True)

@app.route('/export/pdf')
def export_pdf():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM history ORDER BY timestamp DESC').fetchall()
    conn.close()
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "Inventory Transaction Report")
    y = 770
    for log in logs:
        p.drawString(100, y, f"{log['timestamp']} | {log['item_name']} | {log['amount']} | {log['type']} | {log['user_name']}")
        y -= 20
        if y < 50: p.showPage(); y = 800
    p.showPage(); p.save(); buffer.seek(0)
    return send_file(buffer, download_name="inventory_report.pdf", as_attachment=True)

# --- จัดการข้อมูล ---
@app.route('/add', methods=['POST'])
def add():
    file = request.files.get('file')
    filename = ""
    if file and file.filename != '':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        filename = "/static/uploads/" + file.filename
    conn = get_db_connection()
    conn.execute('INSERT INTO items (name, unit, image_path) VALUES (?, ?, ?)', 
                 (request.form['name'], request.form['unit'], filename))
    conn.commit(); conn.close()
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
        conn.commit(); conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run()
