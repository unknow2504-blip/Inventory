from flask import Flask, render_template_string, request, redirect, send_file
import sqlite3
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
import os
from werkzeug.utils import secure_filename

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
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS items 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, unit TEXT, balance INTEGER DEFAULT 0, image_path TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS history 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, amount INTEGER, type TEXT, user_name TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

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
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: auto; padding: 20px; background: #f0f2f5; }
            .nav { margin-bottom: 20px; padding: 15px; background: white; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
            table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            th, td { padding: 15px; border-bottom: 1px solid #eee; text-align: left; }
            th { background: #007bff; color: white; }
            .btn-add { background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
            input { padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        </style>

        <div class="nav">
            <a href="/" style="text-decoration:none; color:#007bff; font-weight:bold;">🏠 หน้าหลักคลังสินค้า</a> | 
            <a href="/history" style="text-decoration:none; color:#555;">📜 ดูประวัติการเบิก-รับ</a>
        </div>

        <h1>📦 ระบบจัดการคลังสินค้า</h1>
        
        <form method="get" style="margin-bottom: 20px;">
            <input name="search" placeholder="ค้นหาชื่ออุปกรณ์..." value="{{ search }}" style="width:250px;">
            <button type="submit" style="padding:10px; cursor:pointer;">🔍 ค้นหา</button>
        </form>

        <div style="background: white; padding: 20px; border-radius: 10px; margin-bottom: 25px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
            <h3 style="margin-top:0;">➕ เพิ่มอุปกรณ์ใหม่</h3>
            <form action="/add" method="post" enctype="multipart/form-data" style="display: flex; gap: 10px; flex-wrap: wrap;">
                <input name="name" placeholder="ชื่อของ" required>
                <input name="unit" placeholder="หน่วย (ชิ้น/กล่อง)" required>
                <input type="file" name="file" accept="image/*">
                <button type="submit" class="btn-add">บันทึกเข้าคลัง</button>
            </form>
        </div>

        <table>
            <tr><th>รูป</th><th>ชื่ออุปกรณ์</th><th>ยอดคงเหลือ</th><th>จัดการ</th></tr>
            {% for item in items %}
            <tr>
                <td style="text-align:center;">
                    {% if item.image_path %}
                        <img src="{{ item.image_path }}" width="60" height="60" style="object-fit:cover; border-radius:5px;">
                    {% else %} <span style="color:#ccc;">ไม่มีรูป</span> {% endif %}
                </td>
                <td><strong>{{ item.name }}</strong><br><small style="color:#666;">หน่วย: {{ item.unit }}</small></td>
                <td style="font-size: 1.3em; font-weight:bold; color:#007bff;">{{ item.balance }}</td>
                <td>
                    <form action="/update" method="post" style="display:flex; gap:5px;">
                        <input type="hidden" name="id" value="{{ item.id }}">
                        <input name="user_name" placeholder="ผู้ทำรายการ" required style="width:100px;">
                        <input type="number" name="amount" style="width:60px;" required min="1" placeholder="จำนวน">
                        <button name="type" value="IN" style="background:#007bff; color:white; border:none; padding:8px 12px; border-radius:4px; cursor:pointer;">รับ</button>
                        <button name="type" value="OUT" style="background:#dc3545; color:white; border:none; padding:8px 12px; border-radius:4px; cursor:pointer;">เบิก</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    ''', items=items, search=search)

# --- หน้าประวัติ: ดูย้อนหลัง + Export ---
@app.route('/history')
def history():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM history ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template_string('''
        <style>
            body { font-family: sans-serif; max-width: 900px; margin: auto; padding: 20px; background: #f4f7f6; }
            .nav-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .nav-btn { text-decoration: none; padding: 10px 15px; border-radius: 5px; font-weight: bold; }
            .btn-back { background: white; color: #333; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .btn-excel { background: #28a745; color: white; }
            .btn-pdf { background: #dc3545; color: white; }
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            .type-IN { color: #28a745; font-weight: bold; }
            .type-OUT { color: #dc3545; font-weight: bold; }
        </style>
        
        <div class="nav-container">
            <a href="/" class="nav-btn btn-back">🏠 กลับหน้าหลัก</a>
            <div>
                <a href="/export/excel" class="nav-btn btn-excel">📊 โหลด Excel</a>
                <a href="/export/pdf" class="nav-btn btn-pdf">📄 โหลด PDF</a>
            </div>
        </div>

        <h1>📜 ประวัติการเบิก-รับของ</h1>
        <table>
            <tr><th>วัน-เวลา</th><th>ชื่ออุปกรณ์</th><th>จำนวน</th><th>ประเภท</th><th>ผู้ทำรายการ</th></tr>
            {% for log in logs %}
            <tr>
                <td>{{ log.timestamp }}</td>
                <td>{{ log.item_name }}</td>
                <td>{{ log.amount }}</td>
                <td class="type-{{ log.type }}">{{ "📥 รับเข้า" if log.type == "IN" else "📤 เบิกออก" }}</td>
                <td>{{ log.user_name }}</td>
            </tr>
            {% endfor %}
        </table>
    ''', logs=logs)

# --- Logic: เพิ่ม/อัปเดต/Export ---

@app.route('/add', methods=['POST'])
def add():
    file = request.files.get('file')
    filename = ""
    if file and file.filename != '':
        fname = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        filename = "/static/uploads/" + fname
    
    with get_db_connection() as conn:
        conn.execute('INSERT INTO items (name, unit, image_path) VALUES (?, ?, ?)', 
                     (request.form['name'], request.form['unit'], filename))
    return redirect('/')

@app.route('/update', methods=['POST'])
def update():
    item_id, amount = request.form['id'], int(request.form['amount'])
    t_type, user = request.form['type'], request.form['user_name']
    
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if item:
        # ป้องกันยอดติดลบ
        new_bal = item['balance'] + amount if t_type == 'IN' else item['balance'] - amount
        if new_bal < 0:
             return "ยอดคงเหลือไม่พอสำหรับการเบิก!", 400
             
        with conn:
            conn.execute('UPDATE items SET balance = ? WHERE id = ?', (new_bal, item_id))
            conn.execute('INSERT INTO history (item_name, amount, type, user_name) VALUES (?, ?, ?, ?)',
                         (item['name'], amount, t_type, user))
    conn.close()
    return redirect('/')

@app.route('/export/excel')
def export_excel():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT timestamp, item_name, amount, type, user_name FROM history ORDER BY timestamp DESC", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Log')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="inventory_history.xlsx")

@app.route('/export/pdf')
def export_pdf():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM history ORDER BY timestamp DESC').fetchall()
    conn.close()
    output = BytesIO()
    p = canvas.Canvas(output, pagesize=A4)
    p.drawString(100, 800, "Inventory Transaction History")
    y = 750
    for log in logs:
        text = f"{log['timestamp']} | {log['item_name']} | {log['amount']} | {log['type']} | {log['user_name']}"
        p.drawString(50, y, text)
        y -= 20
        if y < 50: p.showPage(); y = 800
    p.save()
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="inventory_history.pdf")

if __name__ == '__main__':
    # สำหรับ Render: ใช้ PORT จาก environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

