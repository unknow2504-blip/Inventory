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
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ตรวจสอบโฟลเดอร์รูปภาพ
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

# --- Routes เพิ่มเติม: Export ข้อมูล ---

@app.route('/export/excel')
def export_excel():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM history", conn)
    conn.close()
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='History')
    output.seek(0)
    
    return send_file(output, attachment_filename="inventory_history.xlsx", as_attachment=True)

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
    item_id = request.form['id']
    amount = int(request.form['amount'])
    t_type = request.form['type']
    user = request.form['user_name']
    
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    
    if item:
        # ตรวจสอบไม่ให้เบิกเกินยอดคงเหลือ
        if t_type == 'OUT' and item['balance'] < amount:
            conn.close()
            return "Error: สินค้าในคลังไม่พอให้เบิก!", 400
            
        new_bal = item['balance'] + amount if t_type == 'IN' else item['balance'] - amount
        
        with conn:
            conn.execute('UPDATE items SET balance = ? WHERE id = ?', (new_bal, item_id))
            conn.execute('INSERT INTO history (item_name, amount, type, user_name) VALUES (?, ?, ?, ?)',
                         (item['name'], amount, t_type, user))
    conn.close()
    return redirect('/')

# (คงส่วน index และ history ไว้ตามเดิม หรือเพิ่มปุ่ม Export ในหน้า History)

