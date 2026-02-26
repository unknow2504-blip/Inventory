from flask import Flask, render_template_string, request, redirect
import sqlite3, os

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

# หน้าหลัก: เน้นใช้ง่าย มีกล่องเพิ่มของ และตารางเบิกจ่าย
@app.route('/')
def index():
    search = request.args.get('search', '')
    conn = get_db()
    items = conn.execute("SELECT * FROM items WHERE name LIKE ?", ('%'+search+'%',)).fetchall() if search else conn.execute("SELECT * FROM items").fetchall()
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
        path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(path)
        filename = "/static/uploads/" + file.filename
    conn = get_db()
    conn.execute("INSERT INTO items (name, unit, image_path) VALUES (?, ?, ?)", (request.form['name'], request.form['unit'], filename))
    conn.commit()
    conn.close()
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
    conn.close()
    return redirect('/')

# --- ดีไซน์ที่ทำให้ไม่เละ ---
HTML_MAIN = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; background: #f4f7f6; padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .btn { padding: 8px 15px; border-radius: 4px; border: none; cursor: pointer; color: white; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
    </style>
</head>
<body>
    <div style="max-width: 900px; margin: auto;">
        <div style="display:flex; justify-content: space-between; align-items: center;">
            <h2>📦 ระบบคลัง</h2>
            <a href="/history" style="text-decoration:none; color:#007bff;">📜 ดูประวัติย้อนหลัง</a>
        </div>

        <div class="card" style="border-top: 5px solid #28a745;">
            <h3 style="margin-top:0;">➕ เพิ่มของใหม่เข้าคลัง</h3>
            <form action="/add" method="post" enctype="multipart/form-data" style="display:flex; gap:10px; flex-wrap: wrap;">
                <input name="name" placeholder="ชื่ออุปกรณ์" required style="padding:8px; flex:2;">
                <input name="unit" placeholder="หน่วย" required style="padding:8px; flex:1;">
                <input type="file" name="file" style="flex:1;">
                <button type="submit" class="btn" style="background:#28a745;">บันทึก</button>
            </form>
        </div>

        <div class="card">
            <form method="get" style="margin-bottom:15px; display:flex; gap:10px;">
                <input name="search" placeholder="ค้นหาชื่อของ..." value="{{ search }}" style="flex:1; padding:8px;">
                <button type="submit" class="btn" style="background:#6c757d;">🔍 ค้นหา</button>
            </form>
            <table>
                <tr style="background:#007bff; color:white;"><th>รูป</th><th>ชื่อ</th><th>คงเหลือ</th><th>จัดการ</th></tr>
                {% for item in items %}
                <tr>
                    <td>{% if item.image_path %}<img src="{{ item.image_path }}" width="50">{% endif %}</td>
                    <td>{{ item.name }} ({{ item.unit }})</td>
                    <td style="font-weight:bold; color:#007bff; font-size:1.2em;">{{ item.balance }}</td>
                    <td>
                        <form action="/update" method="post" style="display:flex; gap:5px;">
                            <input type="hidden" name="id" value="{{ item.id }}">
                            <input name="user" placeholder="คนทำรายการ" required style="width:80px; padding:5px;">
                            <input type="number" name="amount" value="1" style="width:40px; padding:5px;">
                            <button name="type" value="IN" class="btn" style="background:#007bff; padding:5px;">รับ</button>
                            <button name="type" value="OUT" class="btn" style="background:#dc3545; padding:5px;">เบิก</button>
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
<head><meta charset="UTF-8"><style>body{font-family:sans-serif; padding:20px; max-width:800px; margin:auto;}</style></head>
<body>
    <a href="/">⬅ กลับหน้าหลัก</a>
    <h2>📜 ประวัติย้อนหลัง</h2>
    <table border="1" style="width:100%; border-collapse: collapse;">
        <tr style="background:#eee;"><th>วัน-เวลา</th><th>ชื่อของ</th><th>จำนวน</th><th>สถานะ</th><th>ผู้ทำ</th></tr>
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

