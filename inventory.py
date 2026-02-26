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
            body { font-family: sans-serif; max-width: 900px; margin: auto; padding: 20px; background: #f4f7f6; }
            .nav { margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; gap: 20px; }
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            th { background: #007bff; color: white; }
            .btn-add { background: #28a745; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer; }
            input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        </style>

        <div class="nav">
            <a href="/">🏠 หน้าหลักคลังสินค้า</a>
            <a href="/history">📜 ดูประวัติการเบิก-รับ</a>
        </div>

        <h1>📦 ระบบจัดการคลังสินค้า</h1>
        
        <form method="get" style="margin-bottom: 20px; display: flex; gap: 10px;">
            <input name="search" placeholder="ค้นหาชื่ออุปกรณ์..." value="{{ search }}" style="flex-grow: 1;">
            <button type="submit">🔍 ค้นหา</button>
            {% if search %}<a href="/"><button type="button">ล้าง</button></a>{% endif %}
        </form>

        <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h3>➕ เพิ่มอุปกรณ์ใหม่ (เลือกรูปจากเครื่อง)</h3>
            <form action="/add" method="post" enctype="multipart/form-data" style="display: flex; gap: 10px; flex-wrap: wrap;">
                <input name="name" placeholder="ชื่อของ" required>
                <input name="unit" placeholder="หน่วย (ชิ้น/กล่อง)" required>
                <input type="file" name="file" accept="image/*">
                <button type="submit" class="btn-add">บันทึกเข้าคลัง</button>
            </form>
        </div>

        <table>
            <tr><th>รูป</th><th>ชื่ออุปกรณ์</th><th>คงเหลือ</th><th>จัดการ (ระบุชื่อผู้เบิก)</th></tr>
            {% for item in items %}
            <tr>
                <td style="text-align:center;">
                    {% if item.image_path %}
                        <img src="{{ item.image_path }}" width="60" height="60" style="object-fit: cover; border-radius:4px;">
                    {% else %} <span style="color:#ccc;">No Pic</span> {% endif %}
                </td>
                <td><strong>{{ item.name }}</strong><br><small>หน่วย: {{ item.unit }}</small></td>
                <td style="font-size: 1.2em; text-align: center;">{{ item.balance }}</td>
                <td>
                    <form action="/update" method="post" style="display: flex; gap: 5px;">
                        <input type="hidden" name="id" value="{{ item.id }}">
                        <input name="user_name" placeholder="คนทำรายการ" required style="width:100px;">
                        <input type="number" name="amount" style="width:50px;" required min="1" value="1">
                        <button name="type" value="IN" style="background:#007bff; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">รับ</button>
                        <button name="type" value="OUT" style="background:#dc3545; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">เบิก</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    ''', items=items, search=search)

# --- หน้าประวัติ: ดูย้อนหลัง + ปุ่มดาวน์โหลด ---
@app.route('/history')
def history():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM history ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template_string('''
        <style>
            body { font-family: sans-serif; max-width: 900px; margin: auto; padding: 20px; background: #f4f7f6; }
            .nav { margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; display: flex; gap: 20px; }
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            th { background: #6c757d; color: white; }
            .type-IN { color: #28a745; font-weight: bold; }
            .type-OUT { color: #dc3545; font-weight: bold; }
            .export-btns { margin-bottom: 15px; display: flex; gap: 10px; }
            .btn-ex { padding: 10px 15px; border: none; border-radius: 4px; color: white; cursor: pointer; text-decoration: none; font-size: 14px; }
        </style>
        <div class="nav"><a href="/">🏠 กลับหน้าหลัก</a></div>
        <h1>📜 ประวัติการเบิก-รับของ</h1>
        
        <div class="export-btns">
            <a href="/export/excel" class="btn-ex" style="background: #1d6f42;">💾 ดาวน์โหลด Excel (.xlsx)</a>
            <a href="/export/pdf" class="btn-ex" style="background: #c1311b;">📄 ดาวน์โหลด PDF (.pdf)</a>
        </div>

        <table>
            <tr><th>วัน-เวลา</th><th>ชื่ออุปกรณ์</th><th>จำนวน</th><th>ประเภท</th><th>ผู้ทำรายการ</th></tr>
            {% for log in logs %}
            <tr>
                <td style="font-size: 0.85em; color: #666;">{{ log.timestamp }}</td>
                <td>{{ log.item_name }}</td>
                <td>{{ log.amount }}</td>
                <td class="type-{{ log.type }}">{{ "✅ รับเข้า" if log.type == "IN" else "📤 เบิกออก" }}</td>
                <td>{{ log.user_name }}</td>
            </tr>
            {% endfor %}
        </table>
    ''', logs=logs)

# --- ส่วน Export ข้อมูล ---
@app.route('/export/excel')
def export_excel():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM history ORDER BY timestamp DESC", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='TransactionHistory')
    output.seek(0)
    return send_file(output, download_name="history_report.xlsx", as_attachment=True)

@app.route('/export/pdf')
def export_pdf():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM history ORDER BY timestamp DESC').fetchall()
    conn.close()
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "Inventory Transaction Report")
    p.setFont("Helvetica", 10)
    y = 770
    p.drawString(100, y, "Date/Time | Item Name | Qty | Type | User")
    p.line(100, y-5, 500, y-5)
    y -= 20
    for log in logs:
        p.drawString(100, y, f"{log['timestamp']} | {log['item_name']} | {log['amount']} | {log['type']} | {log['user_name']}")
        y -= 15
        if y < 50: p.showPage(); y = 800
    p.showPage(); p.save(); buffer.seek(0)
    return send_file(buffer, download_name="history_report.pdf", as_attachment=True)

# --- ส่วนจัดการข้อมูล (Add/Update) ---
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

