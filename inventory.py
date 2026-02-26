from flask import Flask, render_template_string, request, redirect, send_file
import sqlite3, os, pandas as pd
from reportlab.pdfgen import canvas
from io import BytesIO

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    search = request.args.get('search', '')
    conn = get_db()
    if search:
        items = conn.execute("SELECT * FROM items WHERE name LIKE ?", ('%'+search+'%',)).fetchall()
    else:
        items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    return render_template_string(HTML_MAIN, items=items, search=search)

@app.route('/history')
def history():
    conn = get_db()
    logs = conn.execute('SELECT * FROM history ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template_string(HTML_HISTORY, logs=logs)

# --- ปุ่มส่งออกไฟล์ ---
@app.route('/export/excel')
def export_excel():
    conn = get_db()
    df = pd.read_sql_query("SELECT timestamp, item_name, amount, type, user_name FROM history", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="history.xlsx", as_attachment=True)

@app.route('/export/pdf')
def export_pdf():
    conn = get_db()
    logs = conn.execute('SELECT * FROM history ORDER BY timestamp DESC').fetchall()
    conn.close()
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "Inventory Report")
    y = 770
    for log in logs:
        p.drawString(100, y, f"{log['timestamp']} | {log['item_name']} | {log['amount']} | {log['type']} | {log['user_name']}")
        y -= 20
    p.save(); buffer.seek(0)
    return send_file(buffer, download_name="report.pdf", as_attachment=True)

# --- ระบบจัดการข้อมูล ---
@app.route('/add', methods=['POST'])
def add():
    file = request.files.get('file')
    filename = ""
    if file and file.filename:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        filename = "/static/uploads/" + file.filename
    conn = get_db()
    conn.execute('INSERT INTO items (name, unit, image_path) VALUES (?, ?, ?)', (request.form['name'], request.form['unit'], filename))
    conn.commit(); conn.close()
    return redirect('/')

@app.route('/update', methods=['POST'])
def update():
    id, amt, t_type, user = request.form['id'], int(request.form['amount']), request.form['type'], request.form['user_name']
    conn = get_db()
    item = conn.execute('SELECT * FROM items WHERE id=?', (id,)).fetchone()
    if item:
        new_bal = item['balance'] + amt if t_type == 'IN' else item['balance'] - amt
        conn.execute('UPDATE items SET balance=? WHERE id=?', (max(0, new_bal), id))
        conn.execute('INSERT INTO history (item_name, amount, type, user_name) VALUES (?, ?, ?, ?)', (item['name'], amt, t_type, user))
        conn.commit(); conn.close()
    return redirect('/')

HTML_MAIN = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; background: #f4f7f6; padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #007bff; color: white; }
    </style>
</head>
<body>
    <div style="max-width: 900px; margin: auto;">
        <div style="display:flex; justify-content: space-between; align-items: center;">
            <h2>📦 ระบบคลังสินค้า</h2>
            <a href="/history">📜 ดูประวัติการเบิก-รับ</a>
        </div>
        
        <div class="card" style="border-top: 5px solid #28a745;">
            <h3>➕ เพิ่มอุปกรณ์ใหม่</h3>
            <form action="/add" method="post" enctype="multipart/form-data" style="display: flex; gap: 10px;">
                <input name="name" placeholder="ชื่อของ" required style="flex:2; padding:8px;">
                <input name="unit" placeholder="หน่วย" required style="flex:1; padding:8px;">
                <input type="file" name="file" style="flex:1;">
                <button type="submit" style="background:#28a745; color:white; border:none; padding:10px; border-radius:4px; cursor:pointer;">บันทึก</button>
            </form>
        </div>

        <div class="card">
            <form method="get" style="margin-bottom:15px;"><input name="search" placeholder="ค้นหาชื่ออุปกรณ์..." value="{{ search }}" style="padding:8px; width:200px;"> <button type="submit">🔍 ค้นหา</button></form>
            <table>
                <tr><th>รูป</th><th>ชื่ออุปกรณ์</th><th>คงเหลือ</th><th>จัดการ</th></tr>
                {% for item in items %}
                <tr>
                    <td>{% if item.image_path %}<img src="{{ item.image_path }}" width="50">{% else %}-{% endif %}</td>
                    <td>{{ item.name }} ({{ item.unit }})</td>
                    <td style="font-weight:bold; color:#007bff;">{{ item.balance }}</td>
                    <td>
                        <form action="/update" method="post" style="display:flex; gap:5px;">
                            <input type="hidden" name="id" value="{{ item.id }}">
                            <input name="user_name" placeholder="ชื่อคนทำ" required style="width:80px;">
                            <input type="number" name="amount" value="1" style="width:40px;">
                            <button name="type" value="IN" style="background:#007bff; color:white; border:none; padding:5px;">รับ</button>
                            <button name="type" value="OUT" style="background:#dc3545; color:white; border:none; padding:5px;">เบิก</button>
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
<head><meta charset="UTF-8"><style>body{font-family:sans-serif; padding:20px; max-width:900px; margin:auto;} table{width:100%; border-collapse:collapse;} th,td{padding:10px; border:1px solid #ddd;}</style></head>
<body>
    <a href="/">⬅ กลับหน้าหลัก</a>
    <h2>📜 ประวัติการเบิก-รับ</h2>
    <div style="margin-bottom:15px;">
        <a href="/export/excel" style="background:#1d6f42; color:white; padding:8px 15px; text-decoration:none; border-radius:4px;">Excel</a>
        <a href="/export/pdf" style="background:#c1311b; color:white; padding:8px 15px; text-decoration:none; border-radius:4px;">PDF</a>
    </div>
    <table>
        <tr style="background:#eee;"><th>วัน-เวลา</th><th>ชื่อของ</th><th>จำนวน</th><th>ประเภท</th><th>คนทำ</th></tr>
        {% for log in logs %}
        <tr><td>{{ log.timestamp }}</td><td>{{ log.item_name }}</td><td>{{ log.amount }}</td><td>{{ "รับเข้า" if log.type == "IN" else "เบิกออก" }}</td><td>{{ log.user_name }}</td></tr>
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

