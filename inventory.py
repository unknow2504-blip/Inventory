from flask import Flask, render_template_string, request, redirect, send_file
import sqlite3, os, pandas as pd
from io import BytesIO

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

# หน้าหลัก: เน้นดูของและเบิกจ่าย
@app.route('/')
def index():
    search = request.args.get('search', '')
    conn = get_db()
    items = conn.execute("SELECT * FROM items WHERE name LIKE ?", ('%'+search+'%',)).fetchall() if search else conn.execute("SELECT * SELECT * FROM items").fetchall()
    conn.close()
    return render_template_string(HTML_MAIN, items=items, search=search)

# หน้าประวัติ: แยกออกมาต่างหาก ไม่ให้ปนกัน
@app.route('/history')
def history():
    conn = get_db()
    logs = conn.execute("SELECT * FROM history ORDER BY timestamp DESC").fetchall()
    conn.close()
    return render_template_string(HTML_HISTORY, logs=logs)

# --- ส่วนรับข้อมูล (Add/Update) ---
@app.route('/add', methods=['POST'])
def add():
    file = request.files.get('file')
    filename = ""
    if file and file.filename:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        filename = "/static/uploads/" + file.filename
    conn = get_db()
    conn.execute("INSERT INTO items (name, unit, image_path) VALUES (?, ?, ?)", (request.form['name'], request.form['unit'], filename))
    conn.commit()
    return redirect('/')

@app.route('/update', methods=['POST'])
def update():
    id, amt, t_type, user = request.form['id'], int(request.form['amount']), request.form['type'], request.form['user']
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (id,)).fetchone()
    new_bal = item['balance'] + amt if t_type == 'IN' else item['balance'] - amt
    conn.execute("UPDATE items SET balance=? WHERE id=?", (max(0, new_bal), id))
    conn.execute("INSERT INTO history (item_name, amount, type, user_name) VALUES (?, ?, ?, ?)", (item['name'], amt, t_type, user))
    conn.commit()
    return redirect('/')

# --- ดีไซน์หน้าเว็บ (แยกเก็บเป็นตัวแปรจะได้ไม่เละ) ---
HTML_MAIN = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <style>
        <style>
    .card-add-item {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 30px;
        border-top: 5px solid #28a745; /* แถบสีเขียวด้านบนให้ดูเด่น */
    }
    .form-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin-bottom: 15px;
    }
    .form-group label {
        display: block;
        margin-bottom: 5px;
        font-weight: bold;
        color: #333;
    }
    .form-group input {
        width: 100%;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 5px;
        box-sizing: border-box; /* ป้องกัน input ล้นขอบ */
    }
    .btn-submit {
        background: #28a745;
        color: white;
        padding: 12px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-size: 16px;
        font-weight: bold;
        width: 100%;
        transition: background 0.3s;
    }
    .btn-submit:hover {
        background: #218838;
    }
</style>

<div class="card-add-item">
    <h3 style="margin-top: 0; color: #28a745;">➕ ลงทะเบียนอุปกรณ์ใหม่</h3>
    <form action="/add" method="post" enctype="multipart/form-data">
        <div class="form-grid">
            <div class="form-group">
                <label>ชื่ออุปกรณ์/พัสดุ:</label>
                <input type="text" name="name" placeholder="เช่น กระดาษ A4, ปากกา" required>
            </div>
            <div class="form-group">
                <label>หน่วยนับ:</label>
                <input type="text" name="unit" placeholder="เช่น รีม, ด้าม, กล่อง" required>
            </div>
            <div class="form-group">
                <label>รูปภาพประกอบ:</label>
                <input type="file" name="file" accept="image/*">
            </div>
        </div>
        <button type="submit" class="btn-submit">💾 บันทึกข้อมูลลงฐานข้อมูล</button>
    </form>
</div>

    </style>
</head>
<body>
    <div class="container">
        <div style="display:flex; justify-content: space-between;">
            <h2>📦 ระบบคลังพัสดุ</h2>
            <a href="/history">📜 ดูประวัติการเบิก</a>
        </div>

        <div class="card">
            <h4>➕ เพิ่มของใหม่</h4>
            <form action="/add" method="post" enctype="multipart/form-data" style="display:flex; gap:10px;">
                <input name="name" placeholder="ชื่อของ" required style="flex:2;">
                <input name="unit" placeholder="หน่วย" required style="flex:1;">
                <input type="file" name="file" style="flex:1;">
                <button type="submit" class="btn" style="background:#28a745;">บันทึก</button>
            </form>
        </div>

        <div class="card">
            <form method="get"><input name="search" placeholder="ค้นหาชื่อของ..." style="width:70%; padding:8px;"> <button type="submit" class="btn" style="background:#6c757d;">ค้นหา</button></form>
            <table>
                <tr><th>รูป</th><th>ชื่อ</th><th>คงเหลือ</th><th>จัดการ</th></tr>
                {% for item in items %}
                <tr>
                    <td>{% if item.image_path %}<img src="{{ item.image_path }}" width="50">{% endif %}</td>
                    <td>{{ item.name }} ({{ item.unit }})</td>
                    <td style="font-weight:bold; color:#007bff;">{{ item.balance }}</td>
                    <td>
                        <form action="/update" method="post" style="display:flex; gap:5px;">
                            <input type="hidden" name="id" value="{{ item.id }}">
                            <input name="user" placeholder="คนเบิก" required style="width:80px;">
                            <input type="number" name="amount" value="1" style="width:40px;">
                            <button name="type" value="IN" class="btn" style="background:#007bff;">รับ</button>
                            <button name="type" value="OUT" class="btn" style="background:#dc3545;">เบิก</button>
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
<head><style>body{font-family:sans-serif; padding:20px; max-width:800px; margin:auto;} table{width:100%; border-collapse:collapse;} th,td{padding:10px; border:1px solid #ddd;}</style></head>
<body>
    <a href="/">⬅ กลับหน้าหลัก</a>
    <h2>📜 ประวัติย้อนหลัง</h2>
    <table>
        <tr><th>วัน-เวลา</th><th>ชื่อของ</th><th>จำนวน</th><th>ประเภท</th><th>คนทำ</th></tr>
        {% for log in logs %}
        <tr>
            <td>{{ log.timestamp }}</td>
            <td>{{ log.item_name }}</td>
            <td>{{ log.amount }}</td>
            <td style="color:{{ 'green' if log.type=='IN' else 'red' }}">{{ 'รับเข้า' if log.type=='IN' else 'เบิกออก' }}</td>
            <td>{{ log.user_name }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
'''

if __name__ == '__main__':
    # สร้างตารางถ้ายังไม่มี
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, unit TEXT, balance INTEGER DEFAULT 0, image_path TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, amount INTEGER, type TEXT, user_name TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.close()
    app.run()
