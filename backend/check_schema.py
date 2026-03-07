import sqlite3

def check_schema():
    conn = sqlite3.connect('freightiq.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(audit_logs)")
    columns = cursor.fetchall()
    print("Columns in audit_logs:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_schema()
