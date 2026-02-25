from flask import Flask, render_template_string, request, redirect
import sqlite3

app = Flask(__name__)

# --- ส่วนจัดการ Database ---
def get_db_connection():
    conn = sqlite3.connect('office_supplies.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, unit TEXT NOT NULL, balance INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# --- หน้าเว็บหลัก ---
@app.route('/')
def index():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ระบบจัดการคลัง</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; padding: 20px; background: #f4f4f4; }
            table { width: 100%; border-collapse: collapse; background: white; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background: #007bff; color: white; }
            .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            input, button { padding: 10px; margin: 5px 0; width: 100%; box-sizing: border-box; }
            button { background: #28a745; color: white; border: none; cursor: pointer; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>📦 เพิ่มอุปกรณ์ใหม่</h2>
            <form action="/add" method="post">
                <input type="text" name="name" placeholder="ชื่ออุปกรณ์" required>
                <input type="text" name="unit" placeholder="หน่วย (เช่น ชิ้น, กล่อง)" required>
                <button type="submit">เพิ่มเข้าระบบ</button>
            </form>
        </div>
        <table>
            <tr><th>ID</th><th>ชื่อ</th><th>คงเหลือ</th><th>หน่วย</th><th>จัดการ</th></tr>
            {% for item in items %}
            <tr>
                <td>{{ item['id'] }}</td>
                <td>{{ item['name'] }}</td>
                <td><strong>{{ item['balance'] }}</strong></td>
                <td>{{ item['unit'] }}</td>
                <td>
                    <form action="/update" method="post" style="display:flex; gap:5px;">
                        <input type="hidden" name="id" value="{{ item['id'] }}">
                        <input type="number" name="amount" style="width:60px" placeholder="จำนวน" required>
                        <button type="submit" name="type" value="IN" style="background:#007bff">รับ</button>
                        <button type="submit" name="type" value="OUT" style="background:#dc3545">เบิก</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    ''', items=items)

@app.route('/add', methods=['POST'])
def add():
    name, unit = request.form['name'], request.form['unit']
    conn = get_db_connection()
    conn.execute('INSERT INTO items (name, unit) VALUES (?, ?)', (name, unit))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/update', methods=['POST'])
def update():
    item_id, amount, t_type = request.form['id'], int(request.form['amount']), request.form['type']
    conn = get_db_connection()
    item = conn.execute('SELECT balance FROM items WHERE id = ?', (item_id,)).fetchone()
    if item:
        new_bal = item['balance'] + amount if t_type == 'IN' else item['balance'] - amount
        conn.execute('UPDATE items SET balance = ? WHERE id = ?', (max(0, new_bal), item_id))
        conn.commit()
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run()
