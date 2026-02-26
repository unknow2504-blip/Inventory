from flask import Flask, render_template_string, request, redirect, send_file
import sqlite3, os, pandas as pd
from io import BytesIO

app = Flask(__name__) # ตรวจสอบแล้วว่าชื่อ 'app' ถูกต้อง
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

# หน้าหลัก: รวมฟอร์มเพิ่มของ (กล่องสีเขียว) และตารางรายการ
@app.route('/')
def index():
    search = request.args.get('search', '')
    conn = get_db()
    if search:
        items = conn.execute("SELECT * FROM items WHERE name LIKE ?", ('%'+search+'%',)).fetchall()
    else:
        items = conn.execute("SELECT * FROM items").fetchall()
    conn.close()
    return render_template_string(HTML_MAIN, items=items, search=search)

@app.route('/history')
def history():
    conn = get_db()
    logs = conn.execute("SELECT * FROM history ORDER BY timestamp DESC").fetchall()
    conn.close()
    return render_template_string(HTML_HISTORY, logs=logs)

@app.route('/add', methods=['POST'])
def add():
    file = request.files.get('file')
    filename = ""
    if file and file.filename:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        filename = "/static/uploads/" + file.filename
    conn = get_db()
    conn.execute("INSERT INTO items (name, unit, image_path) VALUES (?, ?, ?)", (request.form['name'], request.form['unit'], filename))
    conn.commit(); conn.close()
    return redirect('/')

@app.route('/update', methods=['POST'])
def update():
    id, amt, t_type, user = request.form['id'], int(request.form['amount']), request.form['type'], request.form['user']
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (id,)).fetchone()
    if item:
        new_bal = item['balance'] + amt if t_type == 'IN' else item['balance'] - amt
        conn.execute("UPDATE items SET balance=? WHERE id=?", (max(0, new_bal), id))
        conn.execute("INSERT INTO history (item_name, amount, type, user_name) VALUES (?, ?, ?, ?)", (item['name'], amt, t_type, user))
        conn.commit(); conn.close()
    return redirect('/')

# --- ดีไซน์หน้าเว็บแบบรวมศูนย์ ---
HTML_MAIN = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; background: #f0f2f5; padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; border-top: 5px solid #28a745; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; color: white; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #007bff; color: white; }
    </style>
</head>
<body>
    <div style="max-width: 900px; margin: auto;">
        <div style="display:flex; justify-content: space-between;">
            <h2>📦 ระบบคลังพัสดุ</h2>
            <a href="/history">📜 ดูประวัติย้อนหลัง</a>
        </div>

        <div class="card">
            <h3 style="margin-top:0; color:#28a745;">➕ ลงทะเบียนของชิ้นใหม่</h3>
            <form action="/add" method="post" enctype="multipart/form-data" style="display:grid; grid-template-columns: 1fr 1fr 1fr auto; gap:10px; align-items: end;">
                <div><label>ชื่ออุปกรณ์:</label><br><input name="name" required style="width:100%; padding:8px;"></div>
                <div><label>หน่วยนับ:</label><br><input name="unit" required style="width:100%; padding:8px;"></div>
                <div><label>รูปภาพ:</label><br><input type="file" name="file" style="width:100%;"></div>
                <button type="submit" class="btn" style="background:#28a745;">บันทึก</button>
            </form>
        </div>

        <div style="background: white; padding: 20px; border-radius: 10px;">
            <form method="get" style="display:flex; gap:10px; margin-bottom:15px;">
                <input name="search" placeholder="พิมพ์ชื่อเพื่อค้นหาของ..." value="{{ search }}" style="flex:1; padding:8px;">
                <button type="submit" class="btn" style="background:#007bff;">🔍 ค้นหา</button>
            </form>
            <table>
                <tr><th>รูป</th><th>ชื่อ (หน่วย)</th><th>คงเหลือ</th><th>จัดการ</th></tr>
                {% for item in items %}
                <tr>
                    <td>{% if item.image_path %}<img src="{{ item.image_path }}" width="50">{% else %}-{% endif %}</td>
                    <td><strong>{{ item.name }}</strong> ({{ item.unit }})</td>
                    <td style="font-size:1.2em; color:#007bff;">{{ item.balance }}</td>
                    <td>
                        <form action="/update" method="post" style="display:flex; gap:5px;">
                            <input type="hidden" name="id" value="{{ item.id }}">
                            <input name="user" placeholder="คนเบิก/รับ" required style="width:100px;">
                            <input type="number" name="amount" value="1" min="1" style="width:50px;">
                            <button name="type" value="IN" class="btn" style="background:#007bff; padding:5px 10px;">รับ</button>
                            <button name="type" value="OUT" class="btn" style="background:#dc3545; padding:5px 10px;">เบิก</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
'''

HTML_HISTORY = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><style>body{font-family:sans-serif; padding:20px; max-width:800px; margin:auto; background:#f0f2f5;}</style></head>
<body>
    <a href="/">⬅ กลับหน้าหลัก</a>
    <h2>📜 ประวัติย้อนหลัง</h2>
    <table border="1" style="width:100%; border-collapse: collapse; background:white;">
        <tr style="background:#eee;"><th>วัน-เวลา</th><th>ชื่อของ</th><th>จำนวน</th><th>ประเภท</th><th>คนทำ</th></tr>
        {% for log in logs %}
        <tr><td>{{ log.timestamp }}</td><td>{{ log.item_name }}</td><td>{{ log.amount }}</td>
        <td style="color:{{ 'green' if log.type=='IN' else 'red' }}">{{ 'รับเข้า' if log.type=='IN' else 'เบิกออก' }}</td>
        <td>{{ log.user_name }}</td></tr>
        {% endfor %}
    </table>
</body>
</html>
'''

if __name__ == '__main__':
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, unit TEXT, balance INTEGER DEFAULT 0, image_path TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, amount INTEGER, type TEXT, user_name TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.close()
    app.run()
