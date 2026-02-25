import sqlite3
import os

class OfficeInventory:
    def __init__(self, db_name='office_supplies.db'):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # สร้างตารางอุปกรณ์
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                unit TEXT NOT NULL,
                balance INTEGER DEFAULT 0
            )
        ''')
        # สร้างตารางประวัติธุรกรรม
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                t_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                type TEXT, -- IN, OUT, DISPOSE
                amount INTEGER,
                remark TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items (id)
            )
        ''')
        self.conn.commit()

    def add_new_item(self, name, unit):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO items (name, unit) VALUES (?, ?)", (name, unit))
        self.conn.commit()
        print(f"✅ เพิ่ม '{name}' เข้าระบบเรียบร้อย!")

    def update_stock(self, item_id, amount, t_type, remark=""):
        cursor = self.conn.cursor()
        # เช็คยอดปัจจุบันก่อนถ้าจะเอาออก
        cursor.execute("SELECT balance, name FROM items WHERE id = ?", (item_id,))
        res = cursor.fetchone()
        if not res:
            print("❌ ไม่พบรหัสอุปกรณ์นี้")
            return
        
        current_balance, name = res
        
        if t_type in ['OUT', 'DISPOSE'] and current_balance < amount:
            print(f"❌ ยอดคงเหลือไม่พอ! (มีอยู่ {current_balance} {name})")
            return
        # บันทึกธุรกรรม
        cursor.execute("INSERT INTO transactions (item_id, type, amount, remark) VALUES (?, ?, ?, ?)",
                       (item_id, t_type, amount, remark))
        
        # อัปเดตยอดคงเหลือ
        new_balance = current_balance + amount if t_type == 'IN' else current_balance - amount
        cursor.execute("UPDATE items SET balance = ? WHERE id = ?", (new_balance, item_id))
        
        self.conn.commit()
        print(f"✅ บันทึกรายการ {t_type} จำนวน {amount} สำหรับ {name} เรียบร้อย")

    def show_inventory(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, balance, unit FROM items")
        rows = cursor.fetchall()
        print("\n" + "="*50)
        print(f"{'ID':<5} | {'ชื่ออุปกรณ์':<20} | {'คงเหลือ':<10} | {'หน่วย'}")
        print("-" * 50)
        for row in rows:
            print(f"{row[0]:<5} | {row[1]:<20} | {row[2]:<10} | {row[3]}")
        print("="*50 + "\n")

# --- ส่วนของการรันโปรแกรม (Main Menu) ---
def main():
    app = OfficeInventory()
    
    while True:
        print("--- ระบบจัดการวัสดุอุปกรณ์สำนักงาน ---")
        print("1. ดูรายการอุปกรณ์คงเหลือ")
        print("2. เพิ่มอุปกรณ์ใหม่")
        print("3. รับของเข้า (Stock IN)")
        print("4. เบิกใช้งาน (Stock OUT)")
        print("5. จำหน่ายออก/คัดทิ้ง (DISPOSE)")
        print("0. ออกจากโปรแกรม")
        
        

