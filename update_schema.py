import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rosemary@2006',
    'database': 'policy_claim'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def update_schema():
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 1. Add POLICY_ID to payment
        try:
            print("Adding POLICY_ID to payment table...")
            cursor.execute("ALTER TABLE payment ADD COLUMN POLICY_ID VARCHAR(15)")
            print("[SUCCESS] Added POLICY_ID to payment table.")
        except mysql.connector.Error as err:
            if err.errno == 1060: # Duplicate column name
                print("[INFO] POLICY_ID already exists in payment table.")
            else:
                print(f"[ERROR] Could not add POLICY_ID: {err}")

        # 2. Add TAKEN_DATE to policy_taken
        try:
            print("Adding TAKEN_DATE to policy_taken...")
            cursor.execute("ALTER TABLE policy_taken ADD COLUMN TAKEN_DATE DATE")
            print("[SUCCESS] Added TAKEN_DATE to policy_taken.")
        except mysql.connector.Error as err:
            if err.errno == 1060:
                print("[INFO] TAKEN_DATE already exists in policy_taken.")
            else:
                print(f"[ERROR] Could not add TAKEN_DATE: {err}")

        # 3. Backfill TAKEN_DATE
        try:
            print("Backfilling TAKEN_DATE...")
            cursor.execute("""
                UPDATE policy_taken pt
                JOIN policy p ON pt.POLICY_ID = p.POLICY_ID
                SET pt.TAKEN_DATE = p.START_DATE
                WHERE pt.TAKEN_DATE IS NULL
            """)
            print(f"[SUCCESS] Backfilled {cursor.rowcount} rows in policy_taken.")
        except mysql.connector.Error as err:
            print(f"[ERROR] Backfill failed: {err}")

        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error as err:
        print(f"Connection error: {err}")

if __name__ == "__main__":
    update_schema()
