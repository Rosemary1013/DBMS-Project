import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rosemary@2006',
    'database': 'policy_claim'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def check_data():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        print("--- CUSTOMERS ---")
        cursor.execute("SELECT * FROM customer")
        customers = cursor.fetchall()
        for c in customers:
            print(c)
            
        print("\n--- POLICIES TAKEN ---")
        cursor.execute("SELECT * FROM policy_taken")
        for pt in cursor.fetchall():
            print(pt)
            
        print("\n--- CLAIMS ---")
        cursor.execute("SELECT * FROM claim")
        for cl in cursor.fetchall():
            print(cl)
            
        print("\n--- CUST_CLAIM ---")
        cursor.execute("SELECT * FROM cust_claim")
        for cc in cursor.fetchall():
            print(cc)
            
        print("\n--- POLICY DATA ---")
        cursor.execute("SELECT * FROM policy")
        for p in cursor.fetchall():
            print(p)
            
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_data()
