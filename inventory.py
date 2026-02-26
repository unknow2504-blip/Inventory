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
    items = conn.execute("SELECT * FROM items WHERE name LIKE ?", ('%'+search+'%',)).fetchall() if search else conn.execute("SELECT * FROM items").fetchall()
    conn.close()
    return render_template_string(HTML_MAIN, items=items, search=search)

@app.route('/history')
def history():
    conn = get_db()
    logs = conn.execute("SELECT * FROM history ORDER BY timestamp DESC").fetchall()
    conn.close()
    return render_template_string(HTML_HISTORY, logs=logs)

@app.route('/export/excel')
def export_excel():
    conn = get_db()
    df = pd.read_sql_query("SELECT timestamp, item_name, amount, type, user_name FROM history", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="inventory_report.xlsx", as_attachment=True)

@app.route('/add', methods=['POST'])
def add():
    conn = get_db()
    conn.execute("INSERT INTO items (name, unit) VALUES (?, ?)", (request.form['name'], request.form['unit']))
    conn.commit(); conn.close()
    return redirect('/')

@app.route('/update', methods=['POST'])
def update():
    id, amt, t_type, user = request.form['id'], int(request.form['amount']), request.form['type'], request.form['user_name']
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (id,)).fetchone()
    if item:
        new_bal = item['balance'] + amt if t_type == 'IN' else item['balance'] - amt
        conn.execute("UPDATE items SET balance=? WHERE id=?", (max(0, new_bal), id))
        conn.execute("INSERT INTO history (item_name, amount, type, user_name) VALUES (?, ?, ?, ?)", (item['name'], amt, t_type, user))
        conn.commit(); conn.close()
    return redirect('/')

HTML_MAIN = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><style>body{font-family:sans-serif; background:#f4f7f6; padding:20px;} .card{background:white; padding:20px; border-radius:10px; margin-bottom:20px; border-top:5px solid #28a745;} table{width:100%; border-collapse:collapse;} th,td{padding:10px; border-bottom:1px solid #ddd;}</style></head>
<body>
    <div style="max-width:900px; margin:auto;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h2>📦 ระบบคลังพัสดุ</h2>
            <a href="/history" style="text-decoration:none; color:#007bff; font-weight:bold;">📜 ดูประวัติการเบิก-รับ</a>
        </div>
        <div class="card">
            <h3>➕ เพิ่มพัสดุใหม่</h3>
            <form action="/add" method="post" style="display:flex; gap:10px;">
                <input name="name" placeholder="ชื่อพัสดุ" required style="flex:2; padding:8px;">
                <input name="unit" placeholder="หน่วย" required style="flex:1; padding:8px;">
                <button type="submit" style="background:#28a745; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">บันทึก</button>
            </form>
        </div>
        <div class="card" style="border-top:5px solid #007bff;">
            <table>
                <tr style="background:#007bff; color:white;"><th>ชื่อ (หน่วย)</th><th>คงเหลือ</th><th>จัดการ</th></tr>
                {% for item in items %}
                <tr>
                    <td>{{ item.name }} ({{ item.unit }})</td>
                    <td style="font-weight:bold; color:#007bff; font-size:1.1em;">{{ item.balance }}</td>
                    <td>
                        <form action="/update" method="post" style="display:flex; gap:5px;">
                            <input type="hidden" name="id" value="{{ item.id }}">
                            <input name="user_name" placeholder="ชื่อคนทำ" required style="width:80px; padding:5px;">
                            <input type="number" name="amount" value="1" style="width:40px; padding:5px;">
                            <button name="type" value="IN" style="background:#007bff; color:white; border:none; padding:5px; border-radius:3px; cursor:pointer;">รับ</button>
                            <button name="type" value="OUT" style="background:#dc3545; color:white; border:none; padding:5px; border-radius:3px; cursor:pointer;">เบิก</button>
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
<head><meta charset="UTF-8"><style>body{font-family:sans-serif; padding:20px; max-width:900px; margin:auto; background:#f4f7f6;} table{width:100%; border-collapse:collapse; background:white;} th,td{padding:10px; border:1px solid #ddd;}</style></head>
<body>
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <a href="/" style="text-decoration:none; color:#666;">⬅ กลับหน้าหลัก</a>
        <h2>📜 ประวัติการเบิก-รับ</h2>
    </div>
    <div style="margin-bottom:15px;">
        <a href="/export/excel" style="background:#1d6f42; color:white; padding:10px 15px; text-decoration:none; border-radius:5px; font-weight:bold;">📥 ดาวน์โหลด Excel</a>
    </div>
    <table>
        <tr style="background:#eee;"><th>วัน-เวลา</th><th>ชื่อพัสดุ</th><th>จำนวน</th><th>ประเภท</th><th>ผู้ทำรายการ</th></tr>
        {% for log in logs %}
        <tr><td>{{ log.timestamp }}</td><td>{{ log.item_name }}</td><td>{{ log.amount }}</td>
        <td style="color:{{ 'green' if log.type=='IN' else 'red' }}; font-weight:bold;">{{ "รับเข้า" if log.type=="IN" else "เบิกออก" }}</td>
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
