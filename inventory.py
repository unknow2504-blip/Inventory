from flask import Flask, render_template_string, request, redirect, send_file
import sqlite3
import pandas as pd
from reportlab.pdfgen import canvas
from io import BytesIO

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

# อัปเกรดฐานข้อมูล: เพิ่มช่อง image_url และตารางประวัติ
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS items 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, unit TEXT, balance INTEGER DEFAULT 0, image_url TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS history 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, amount INTEGER, type TEXT, user_name TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.close()

init_db()

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
        <h1>📦 ระบบจัดการคลัง Pro</h1>
        
        <form method="get" style="margin-bottom: 20px;">
            <input name="search" placeholder="ค้นหาชื่ออุปกรณ์..." value="{{ search }}">
            <button type="submit">🔍 ค้นหา</button>
            <a href="/">ล้างการค้นหา</a>
        </form>

        <div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 20px;">
            <h3>➕ เพิ่มอุปกรณ์ใหม่</h3>
            <form action="/add" method="post">
                <input name="name" placeholder="ชื่อของ" required>
                <input name="unit" placeholder="หน่วย" required>
                <input name="image_url" placeholder="ลิงก์รูปภาพ (URL)">
                <button type="submit">บันทึก</button>
            </form>
        </div>

        <div style="margin-bottom: 10px;">
            <a href="/export/excel"><button style="background: green; color: white;">💾 โหลด Excel</button></a>
            <a href="/export/pdf"><button style="background: red; color: white;">📄 โหลด PDF</button></a>
        </div>

        <table border="1" style="width:100%; text-align:left;">
            <tr>
                <th>รูปภาพ</th><th>ชื่อ</th><th>คงเหลือ</th><th>หน่วย</th><th>จัดการ (ระบุชื่อผู้เบิกด้วย)</th>
            </tr>
            {% for item in items %}
            <tr>
                <td>
                    {% if item.image_url %}
                        <img src="{{ item.image_url }}" width="50" height="50" style="object-fit: cover;">
                    {% else %}
                        ไม่มีรูป
                    {% endif %}
                </td>
                <td>{{ item.name }}</td>
                <td><strong>{{ item.balance }}</strong></td>
                <td>{{ item.unit }}</td>
                <td>
                    <form action="/update" method="post">
                        <input type="hidden" name="id" value="{{ item.id }}">
                        <input name="user_name" placeholder="ชื่อคนเบิก/รับ" required style="width:100px">
                        <input type="number" name="amount" style="width:50px" required min="1">
                        <button name="type" value="IN">รับเข้า</button>
                        <button name="type" value="OUT">เบิกออก</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    ''', items=items, search=search)

# --- ส่วน Export ข้อมูล ---
@app.route('/export/excel')
def export_excel():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM items", conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    output.seek(0)
    return send_file(output, download_name="inventory.xlsx", as_attachment=True)

@app.route('/export/pdf')
def export_pdf():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "Inventory Report")
    y = 750
    for item in items:
        p.drawString(100, y, f"ID: {item['id']} | {item['name']} : {item['balance']} {item['unit']}")
        y -= 20
    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, download_name="inventory.pdf", as_attachment=True)

# --- ส่วนจัดการ Data (Add/Update) ---
@app.route('/add', methods=['POST'])
def add():
    conn = get_db_connection()
    conn.execute('INSERT INTO items (name, unit, image_url) VALUES (?, ?, ?)', 
                 (request.form['name'], request.form['unit'], request.form['image_url']))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/update', methods=['POST'])
def update():
    item_id = request.form['id']
    amount = int(request.form['amount'])
    t_type = request.form['type']
    user = request.form['user_name']
    
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if item:
        new_bal = item['balance'] + amount if t_type == 'IN' else item['balance'] - amount
        conn.execute('UPDATE items SET balance = ? WHERE id = ?', (max(0, new_bal), item_id))
        # บันทึกลงประวัติ
        conn.execute('INSERT INTO history (item_name, amount, type, user_name) VALUES (?, ?, ?, ?)',
                     (item['name'], amount, t_type, user))
        conn.commit()
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run()
