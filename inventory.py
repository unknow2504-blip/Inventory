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

# --- หน้าแรก: รวมฟอร์มเพิ่มของและตารางเบิกจ่าย ---
@app.route('/')
def index():
    search = request.args.get('search', '')
    conn = get_db()
    if search:
        items = conn.execute("SELECT * FROM items WHERE name LIKE ?", ('%'+search+'%',)).fetchall()
    else:
        items = conn.execute("SELECT * FROM items").fetchall() # แก้ไขจุดที่พิมพ์ซ้ำแล้ว
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

# --- ดีไซน์หน้าเว็บแบบเป็นระเบียบ ---
HTML_MAIN = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; background: #f0f2f5; padding: 20px; }
        .container { max-width: 900px; margin: auto; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .btn { padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; color: white; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #007bff; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div style="display:flex; justify-content: space-between; align-items: center;">
            <h2 style="color: #007bff;">📦 ระบบคลังพัสดุ</h2>
            <a href="/history" style="text-decoration: none; color: #666;">📜 ดูประวัติย้อนหลัง</a>
        </div>

        <div class="card" style="border-top: 4px solid #28a745;">
            <h3 style="margin-top:0; color:#28a745;">➕ ลงทะเบียนของใหม่</h3>
            <form action="/add" method="post" enctype="multipart/form-data" style="display:grid; grid-template-columns: 1fr 1fr 1fr auto; gap:10px; align-items: end;">
                <div><label>ชื่อของ:</label><br><input name="name" required style="width:100%; padding:8px;"></div>
                <div><label>หน่วย:</label><br><input name="unit" required style="width:100%; padding:8px;"></div>
                <div><label>รูป:</label><br><input type="file" name="file" style="width:100%;"></div>
                <button type="submit" class="btn" style="background:#28a745;">บันทึก</button>
            </form>
        </div>

        <div class="card">
            <form method="get" style="display:flex; gap:10px; margin-bottom:15px;">
                <input name="search" placeholder="พิมพ์ชื่อเพื่อค้นหา..." value="{{ search }}" style="flex:1; padding:8px;">
                <button type="submit" class="btn" style="background:#007bff;">🔍 ค้นหา</button>
            </form>
            <table>
                <tr><th>รูป</th><th>ชื่อ (หน่วย)</th><th>คงเหลือ</th><th>จัดการเบิก/รับ</th></tr>
                {% for item in items %}
                <tr>
                    <td>{% if item.image_path %}<img src="{{ item.image_path }}" width="50" height="50" style="object-fit:cover; border-radius:5px;">{% else %}-{% endif %}</td>
                    <td><strong>{{ item.name }}</strong><br><small>{{ item.unit }}</small></td>
                    <td style="font-size:1.2em; color:#007bff;">{{ item.balance }}</td>
                    <td>
                        <form action="/update" method="post" style="display:flex; flex-direction:column; gap:5px;">
                            <input type="hidden" name="id" value="{{ item.id }}">
                            <input name="user" placeholder="ชื่อคนเบิก" required style="padding:5px;">
                            <div style="display:flex; gap:5px;">
                                <input type="number" name="amount" value="1" min="1" style="width:50px; padding:5px;">
                                <button name="type" value="IN" class="btn" style="background:#007bff; flex:1; padding:5px;">รับ</button>
                                <button name="type" value="OUT" class="btn" style="background:#dc3545; flex:1; padding:5px;">เบิก</button>
                            </div>
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
<head><meta charset="UTF-8"><style>body{font-family:sans-serif; padding:20px; max-width:800px; margin:auto; background:#f8f9fa;} table{width:100%; border-collapse:collapse; background:white;} th,td{padding:10px; border:1px solid #ddd;}</style></head>
<body>
    <div style="display:flex; justify-content: space-between;">
        <a href="/" style="text-decoration:none;">

