import sqlite3

def migrate_audit_logs():
    conn = sqlite3.connect('freightiq.db')
    cursor = conn.cursor()
    
    # 1. Check current schema
    cursor.execute("PRAGMA table_info(audit_logs)")
    cols = cursor.fetchall()
    print("Old schema:", cols)
    
    # 2. Rename old table
    cursor.execute("ALTER TABLE audit_logs RENAME TO audit_logs_old")
    
    # 3. Create new table with nullable triplet_id
    # Based on the model and previous schema:
    create_table_sql = """
    CREATE TABLE audit_logs (
        id VARCHAR PRIMARY KEY,
        triplet_id VARCHAR,
        action VARCHAR NOT NULL,
        ai_generated TEXT NOT NULL,
        context JSON,
        user_id VARCHAR,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        document_id VARCHAR,
        FOREIGN KEY(triplet_id) REFERENCES triplets(id),
        FOREIGN KEY(document_id) REFERENCES documents(id)
    )
    """
    cursor.execute(create_table_sql)
    
    # 4. Copy data from old to new
    # We need to map the columns properly
    cursor.execute("""
        INSERT INTO audit_logs (id, triplet_id, action, ai_generated, context, user_id, timestamp, document_id)
        SELECT id, triplet_id, action, ai_generated, context, user_id, timestamp, document_id
        FROM audit_logs_old
    """)
    
    # 5. Drop old table
    cursor.execute("DROP TABLE audit_logs_old")
    
    conn.commit()
    print("Migration complete.")
    conn.close()

if __name__ == "__main__":
    migrate_audit_logs()
