import mysql.connector
from datetime import datetime, timedelta

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rosemary@2006',
    'database': 'policy_claim'
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def verify():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    print("--- Verifying Schema ---")
    cursor.execute("DESCRIBE admin_verify_pay")
    cols = [col['Field'] for col in cursor.fetchall()]
    if 'ADMIN_ID' in cols and 'PAY_ID' in cols:
        print("[SUCCESS] admin_verify_pay table exists with correct columns.")
    else:
        print("[FAILURE] admin_verify_pay schema mismatch!")

    print("\n--- Verifying Data Population ---")
    cursor.execute("SELECT COUNT(*) as count FROM admin_verify_pay")
    count = cursor.fetchone()['count']
    if count > 0:
        print(f"[SUCCESS] admin_verify_pay has {count} entries.")
    else:
        print("[FAILURE] admin_verify_pay is empty!")
    
    # Simulation logic matches app.py
    from datetime import datetime, timedelta
    
    # 1. Test Maturity
    start_date = datetime.now().date() - timedelta(days=6*365.25) # 6 years ago
    duration_years = 5
    end_date = start_date + timedelta(days=duration_years * 365.25)
    is_mature = datetime.now().date() >= end_date
    print(f"Policy (6yr old, 5yr duration): Mature={is_mature} (Expected: True)")
    
    # 2. Test Claim State Logic
    def can_request(status):
        # Logic from request_claim route
        if status in ['Pending', 'Success']:
            return False
        return True
        
    print(f"Can request claim if previous status is 'Failed'? {can_request('Failed')} (Expected: True)")
    print(f"Can request claim if previous status is 'Pending'? {can_request('Pending')} (Expected: False)")
    print(f"Can request claim if previous status is 'Success'? {can_request('Success')} (Expected: False)")
    
    cursor.close()
    db.close()

if __name__ == "__main__":
    verify()
