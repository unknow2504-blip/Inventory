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

# --- 📥 ส่วนคำสั่ง Export ไฟล์ ---

@app.route('/export/excel')
def export_excel():
    conn = get_db()
    df = pd.read_sql_query("SELECT timestamp, item_name, amount, type, user_name FROM history", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='History')
    output.seek(0)
    return send_file(output, download_name="inventory_report.xlsx", as_attachment=True)

@app.route('/export/pdf')
def export_pdf():
    conn = get_db()
    logs = conn.execute("SELECT * FROM history ORDER BY timestamp DESC").fetchall()
    conn.close()
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "Inventory Transaction Report")
    p.setFont("Helvetica", 10)
    y = 770
    p.drawString(50, y, "Date/Time | Item | Qty | Type | User")
    p.line(50, y-5, 550, y-5)
    y -= 25
    for log in logs:
        line = f"{log['timestamp']} | {log['item_name']} | {log['amount']} | {log['type']} | {log['user_name']}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50: p.showPage(); y = 800
    p.showPage(); p.save(); buffer.seek(0)
    return send_file(buffer, download_name="inventory_report.pdf", as_attachment=True)

# --- ส่วนจัดการข้อมูล ---

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
    id, amt, t_type, user = request.form['id'], int(request.form['amount']), request.form['type'], request.form['user_name']
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (id,)).fetchone()
    new_bal = item['balance'] + amt if t_type == 'IN' else item['balance'] - amt
    conn.execute("UPDATE items SET balance=? WHERE id=?", (max(0, new_bal), id))
    conn.execute("INSERT INTO history (item_name, amount, type, user_name) VALUES (?, ?, ?, ?)", (item['name'], amt, t_type, user))
    conn.commit(); conn.close()
    return redirect('/')

# --- ดีไซน์หน้าเว็บ ---

HTML_MAIN = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; background: #f0f2f5; padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; border-top: 5px solid #28a745; }
        .btn { padding: 10px; border: none; border-radius: 5px; cursor: pointer; color: white; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
    </style>
</head>
<body>
    <div style="max-width: 900px; margin: auto;">
        <div style="display:flex; justify-content: space-between; align-items: center;">
            <h2>📦 ระบบคลังพัสดุ</h2>
            <a href="/history" style="text-decoration:none; color:#007bff; font-weight:bold;">📜 ดูประวัติการเบิก-รับ</a>
        </div>

        <div class="card">
            <h3 style="margin-top:0; color:#28a745;">➕ ลงทะเบียนของใหม่</h3>
            <form action="/add" method="post" enctype="multipart/form-data" style="display:grid; grid-template-columns: 1fr 1fr 1fr auto; gap:10px;">
                <input name="name" placeholder="ชื่ออุปกรณ์" required style="padding:8px;">
                <input name="unit" placeholder="หน่วย" required style="padding:8px;">
                <input type="file" name="file">
                <button type="submit" class="btn" style="background:#28a745;">บันทึก</button>
            </form>
        </div>

        <div style="background: white; padding: 20px; border-radius: 10px;">
            <form method="get" style="display:flex; gap:10px; margin-bottom:15px;">
                <input name="search" placeholder="ค้นหาพัสดุ..." value="{{ search }}" style="flex:1; padding:8px;">
                <button type="submit" class="btn" style="background:#007bff;">🔍 ค้นหา</button>
            </form>
            <table>
                <tr style="background:#007bff; color:white;"><th>รูป</th><th>ชื่อ</th><th>คงเหลือ</th><th>จัดการ</th></tr>
                {% for item in items %}
                <tr>
                    <td>{% if item.image_path %}<img src="{{ item.image_path }}" width="50">{% endif %}</td>
                    <td><strong>{{ item.name }}</strong> ({{ item.unit }})</td>
                    <td style="font-size:1.2em; color:#007bff;">{{ item.balance }}</td>
                    <td>
                        <form action="/update" method="post" style="display:flex; gap:5px;">
                            <input type="hidden" name="id" value="{{ item.id }}">
                            <input name="user_name" placeholder="ชื่อคนทำ" required style="width:80px;">
                            <input type="number" name="amount" value="1" min="1" style="width:40px;">
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
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; padding: 20px; max-width: 900px; margin: auto; background: #f0f2f5; }
        .export-bar { background: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; display: flex; gap: 10px; align-items: center; }
        .btn-ex { padding: 8px 15px; border-radius: 5px; color: white; text-decoration: none; font-weight: bold; font-size: 14px; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 10px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <div style="display:flex; justify-content: space-between; align-items: center;">
        <a href="/" style="text-decoration:none; color:#666;">⬅ กลับหน้าหลัก</a>
        <h2>📜 ประวัติการเบิก-รับของ</h2>
    </div>
    
    <div class="export-bar">
        <strong>ดาวน์โหลดรายงาน:</strong>
        <a href="/export/excel" class="btn-ex" style="background: #1d6f42;">💾 Excel (.xlsx)</a>
        <a href="/export/pdf" class="btn-ex" style="background: #c1311b;">📄 PDF (.pdf)</a>
    </div>

    <table>
        <tr style="background:#eee;"><th>วัน-เวลา</th><th>ชื่อของ</th><th>จำนวน</th><th>ประเภท</th><th>ผู้ทำ</th></tr>
        {% for log in logs %}
        <tr>
            <td style="font-size:0.8em; color:#666;">{{ log.timestamp }}</td>
            <td><strong>{{ log.item_name }}</strong></td>
            <td>{{ log.amount }}</td>
            <td style="color:{{ 'green' if log.type=='IN' else 'red' }}; font-weight:bold;">
                {{ 'รับเข้า' if log.type=='IN' else 'เบิกออก' }}
            </td>
            <td>{{ log.user_name }}</td>
        </tr>
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

