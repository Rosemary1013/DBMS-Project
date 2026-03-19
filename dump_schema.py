import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rosemary@2006',
    'database': 'policy_claim'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def dump_schema():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        print(f"\n--- Table: {table} ---")
        cursor.execute(f"DESCRIBE {table}")
        for col in cursor.fetchall():
            print(col)
    
    cursor.close()
    db.close()

if __name__ == "__main__":
    dump_schema()
