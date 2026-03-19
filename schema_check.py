import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rosemary@2006',
    'database': 'policy_claim'
}

try:
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print("Tables:", tables)

    for (table,) in tables:
        print(f"\n--- Schema for {table} ---")
        cursor.execute(f"DESCRIBE {table}")
        columns = cursor.fetchall()
        for col in columns:
            print(col)

    cursor.close()
    db.close()
except Exception as e:
    print("Error:", e)
