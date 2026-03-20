
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
import os
import uuid

app = Flask(__name__, template_folder=os.path.abspath('templates'))
app.secret_key = os.urandom(24)  # Change this to a fixed secret in production

# ─── Database Configuration ───────────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',         # ← your MySQL username
    'password': 'rosemary@2006',  # ← your MySQL password
    'database': 'policy_claim'  # ← your database name
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# Removed hash_password to support plain-text varchar(15) limit
# def hash_password(password):
#     return hashlib.sha256(password.encode()).hexdigest()

def format_duration(td):
    """Convert a timedelta (from MySQL DURATION) into a human-readable string.
    Returns dict with 'text' (display string) and 'total_days' (for calculations)."""
    if not td:
        return {'text': 'N/A', 'total_days': 0}
    
    total_hours = int(td.total_seconds() / 3600)
    # The DB stores duration in hours where hours = years conceptually
    # Convert total_hours to days for calculation
    total_days = int(total_hours * 365.25)
    
    years = total_hours  # each hour unit = 1 year in the DB schema
    
    # But if this is truly a timedelta in days, handle that too
    if td.days > 0:
        total_days = td.days
        years = total_days // 365
        remaining_days = total_days % 365
        months = remaining_days // 30
        days = remaining_days % 30
    else:
        # Fallback: treat total_seconds/3600 as years
        remaining = 0
        months = 0
        days = 0
    
    # Build display string
    parts: list[str] = []
    if years > 0:
        parts.append(f"{years} Year{'s' if years != 1 else ''}")
    if months > 0:
        parts.append(f"{months} Month{'s' if months != 1 else ''}")
    if days > 0:
        parts.append(f"{days} Day{'s' if days != 1 else ''}")
    
    if not parts:
        parts.append("0 Days")
    
    return {
        'text': ' '.join(parts),
        'total_days': total_days,
        'years': years
    }

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    policies = []
    admin_emails = []
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        # Fetch policies and their verification status
        cursor.execute("""
            SELECT p.*, pv.ADMIN_ID as VERIFIED_BY 
            FROM policy p 
            LEFT JOIN policy_verify pv ON p.POLICY_ID = pv.POLICY_ID
        """)
        policies = cursor.fetchall()
        
        # Fetch admin emails for contact section
        cursor.execute("SELECT EMAIL FROM admin_email")
        admin_emails = [row['EMAIL'] for row in cursor.fetchall()]

        for p in policies:
            dur = format_duration(p['DURATION'])
            p['DURATION_DISPLAY'] = dur['text']
            p['DURATION_YEARS'] = dur['years']
        
        # Sort: expired policies go to the end
        policies.sort(key=lambda x: (1 if x.get('STATUS', '').lower() == 'expired' else 0))
        
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error fetching data: {e}")
    return render_template('index.html', policies=policies, admin_emails=admin_emails)

@app.route('/learn-more')
def learn_more():
    return render_template('learn_more.html')

@app.route('/register')
def register():
    return render_template('register.html')

# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = "All fields are required."
        else:
            try:
                db = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT a.ADMIN_ID, a.USERNAME, a.PASSWORD 
                    FROM admin a
                    JOIN admin_email e ON a.ADMIN_ID = e.ADMIN_ID
                    WHERE e.EMAIL = %s
                    """,
                    (email,)
                )
                admin = cursor.fetchone()
                cursor.close()
                db.close()

                if admin and admin['PASSWORD'] == password:
                    session['admin_id']   = admin['ADMIN_ID']
                    session['admin_name'] = admin['USERNAME']
                    return redirect(url_for('admin_dashboard'))
                else:
                    error = "Invalid credentials. Please try again."
            except mysql.connector.Error as e:
                error = f"Database error: {e}"

    return render_template("admin-login.html", error=error)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    stats = {}
    pending_claims = []
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Count Customers
        cursor.execute("SELECT COUNT(*) as count FROM customer")
        stats['customer_count'] = cursor.fetchone()['count']
        
        # Count Agents
        cursor.execute("SELECT COUNT(*) as count FROM agent")
        stats['agent_count'] = cursor.fetchone()['count']
        
        # Count Total Policies
        cursor.execute("SELECT COUNT(*) as count FROM policy")
        stats['policy_count'] = cursor.fetchone()['count']
        
        # Fetch Pending Claims
        cursor.execute("""
            SELECT c.*, p.POLICY_TYPE, p.POLICY_ID, cust.FNAME, cust.MNAME, cust.LNAME 
            FROM claim c 
            JOIN cust_claim cc ON c.CLAIM_ID = cc.CLAIM_ID 
            JOIN policy p ON cc.POLICY_ID = p.POLICY_ID
            JOIN customer cust ON cc.CUST_ID = cust.CUST_ID
            WHERE c.CLAIM_STATUS = 'Pending'
        """)
        pending_claims = cursor.fetchall()
        stats['pending_claims_count'] = len(pending_claims)
        
        # Fetch Processed Claims (History)
        cursor.execute("""
            SELECT c.*, p.POLICY_TYPE, p.POLICY_ID, cust.FNAME, cust.MNAME, cust.LNAME 
            FROM claim c 
            JOIN cust_claim cc ON c.CLAIM_ID = cc.CLAIM_ID 
            JOIN policy p ON cc.POLICY_ID = p.POLICY_ID
            JOIN customer cust ON cc.CUST_ID = cust.CUST_ID
            WHERE c.CLAIM_STATUS IN ('Success', 'Failed')
            ORDER BY c.CLAIM_DATE DESC
        """)
        processed_claims = cursor.fetchall()

        # Fetch All Policies for Verification Management
        cursor.execute("""
            SELECT p.*, pv.ADMIN_ID as VERIFIED_BY 
            FROM policy p 
            LEFT JOIN policy_verify pv ON p.POLICY_ID = pv.POLICY_ID
        """)
        all_policies = cursor.fetchall()
        for p in all_policies:
            dur = format_duration(p['DURATION'])
            p['DURATION_DISPLAY'] = dur['text']
        
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Admin Dashboard error: {e}")

    return render_template('admin-dashboard.html', 
                          admin_name=session['admin_name'],
                          stats=stats,
                          pending_claims=pending_claims,
                          processed_claims=processed_claims,
                          all_policies=all_policies)

@app.route('/admin/policy/verify/<policy_id>', methods=['POST'])
def admin_verify_policy(policy_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    admin_id = session['admin_id']
    try:
        db = get_db()
        cursor = db.cursor()
        # Insert into policy_verify to mark as verified
        cursor.execute("INSERT IGNORE INTO policy_verify (ADMIN_ID, POLICY_ID) VALUES (%s, %s)", (admin_id, policy_id))
        db.commit()
        cursor.close()
        db.close()
        flash(f"Policy {policy_id} verified successfully!", "success")
    except Exception as e:
        flash(f"Error verifying policy: {e}", "error")
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/claim/<claim_id>')
def admin_claim_details(claim_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Get claim and policy info plus TAKEN_DATE
        # Joining via cust_claim which now has the specific CUST_ID
        cursor.execute("""
            SELECT c.*, p.POLICY_TYPE, p.POLICY_ID, pt.TAKEN_DATE, cust.FNAME, cust.MNAME, cust.LNAME, cust.CUST_ID
            FROM claim c
            JOIN cust_claim cc ON c.CLAIM_ID = cc.CLAIM_ID
            JOIN policy p ON cc.POLICY_ID = p.POLICY_ID
            JOIN customer cust ON cc.CUST_ID = cust.CUST_ID
            LEFT JOIN policy_taken pt ON (p.POLICY_ID = pt.POLICY_ID AND cust.CUST_ID = pt.CUST_ID)
            WHERE c.CLAIM_ID = %s
        """, (claim_id,))
        claim = cursor.fetchone()
        
        if not claim:
            cursor.close()
            db.close()
            return f"Claim {claim_id} not found or data mismatch. Check if customer is linked to this policy.", 404
            
        # Get payment history (only verified payments as per admin_verify_pay)
        cursor.execute("""
            SELECT p.* FROM payment p
            JOIN admin_verify_pay avp ON p.PAY_ID = avp.PAY_ID
            WHERE p.POLICY_ID = %s 
            AND p.PAY_ID IN (SELECT PAY_ID FROM cust_pay WHERE CUST_ID = %s)
            ORDER BY p.PAY_DATE DESC
        """, (claim['POLICY_ID'], claim['CUST_ID']))
        payments = cursor.fetchall()
        
        cursor.close()
        db.close()
        return render_template('admin_claim_details.html', claim=claim, payments=payments)
    except Exception as e:
        return f"Error: {e}"

@app.route('/admin/claim/action/<claim_id>/<action>', methods=['POST'])
def admin_claim_action(claim_id, action):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    status = 'Success' if action == 'approve' else 'Failed'
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Update claim status
        cursor.execute("UPDATE claim SET CLAIM_STATUS = %s WHERE CLAIM_ID = %s", (status, claim_id))
        
        if action == 'approve':
            # Record approval
            cursor.execute("INSERT IGNORE INTO claim_apprv (ADMIN_ID, CLAIM_ID) VALUES (%s, %s)", (session['admin_id'], claim_id))
            
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Admin action error: {e}")
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# ─── Customer Routes ──────────────────────────────────────────────────────────

@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    error = None
    next_page = request.args.get('next')
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        next_page = request.form.get('next')

        if not email or not password:
            error = "All fields are required."
        else:
            try:
                db = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT c.CUST_ID, c.FNAME, c.MNAME, c.LNAME, c.PASSWORD 
                    FROM customer c
                    JOIN cust_email e ON c.CUST_ID = e.CUST_ID
                    WHERE e.EMAIL = %s
                    """,
                    (email,)
                )
                customer = cursor.fetchone()
                cursor.close()
                db.close()

                if customer and customer['PASSWORD'] == password:
                    session['customer_id'] = customer['CUST_ID']
                    mname = customer['MNAME'] + " " if customer['MNAME'] else ""
                    session['customer_name'] = f"{customer['FNAME']} {mname}{customer['LNAME']}"
                    if next_page:
                        return redirect(next_page)
                    return redirect(url_for('customer_dashboard'))
                else:
                    error = "Invalid credentials. Please try again."
            except mysql.connector.Error as e:
                error = f"Database error: {e}"

    return render_template("customer-login.html", error=error, next=next_page)

@app.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    error = None
    if request.method == 'POST':
        fname = request.form.get('fname', '').strip()
        mname = request.form.get('mname', '').strip()
        lname = request.form.get('lname', '').strip()
        dob = request.form.get('dob', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        per_addr = request.form.get('per_addr', '').strip()
        comm_addr = request.form.get('comm_addr', '').strip()
        password = request.form.get('password', '')

        if not all([fname, lname, dob, phone, email, per_addr, comm_addr, password]):
            error = "Please fill out all required fields."
        else:
            raw_uid = str(uuid.uuid4().int)
            short_uid = ""
            for i in range(min(6, len(raw_uid))):
                short_uid += raw_uid[i]
            cust_id = f"CUS{short_uid}"
            try:
                db = get_db()
                cursor = db.cursor()
                
                # Check if email exists
                cursor.execute("SELECT * FROM cust_email WHERE EMAIL = %s", (email,))
                if cursor.fetchone():
                    error = "An account with this email already exists."
                    cursor.close()
                    db.close()
                    return render_template("customer-register.html", error=error)

                # Insert into customer table
                agent_id_from_session = session.get('agent_id')
                cursor.execute(
                    """
                    INSERT INTO customer (CUST_ID, FNAME, MNAME, LNAME, DOB, PER_ADDR, COMM_ADDR, PASSWORD, AGENT_ID)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (cust_id, fname, mname, lname, dob, per_addr, comm_addr, password, agent_id_from_session)
                )

                # Insert into cust_email
                cursor.execute(
                    "INSERT INTO cust_email (CUST_ID, EMAIL) VALUES (%s, %s)",
                    (cust_id, email)
                )

                # Insert into cust_phone
                cursor.execute(
                    "INSERT INTO cust_phone (CUST_ID, PHONE) VALUES (%s, %s)",
                    (cust_id, phone)
                )

                # Link agent to customer in AGENT_CUST table
                if agent_id_from_session:
                    cursor.execute(
                        "INSERT INTO agent_cust (AGENT_ID, CUST_ID) VALUES (%s, %s)",
                        (agent_id_from_session, cust_id)
                    )

                db.commit()
                cursor.close()
                db.close()

                # If an agent is doing it, show a success page with the CUST_ID
                if agent_id_from_session:
                    return redirect(url_for('agent_registration_success', cust_id=cust_id))
                
                # Redirect to login page instead of auto-login
                return redirect(url_for('customer_login'))
            except mysql.connector.Error as e:
                error = f"Database error: {e}"

    return render_template("customer-register.html", error=error)

@app.route('/agent/registration_success/<cust_id>')
def agent_registration_success(cust_id):
    if 'agent_id' not in session:
        return redirect(url_for('agent_login'))
    
    customer = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customer WHERE CUST_ID = %s", (cust_id,))
        customer = cursor.fetchone()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error fetching new customer: {e}")
        
    if not customer:
        return "Customer not found", 404
        
    return render_template('agent_registration_success.html', customer=customer)

@app.route('/customer/dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer_id = session['customer_id']
    policies = []
    claims = []
    payments = []
    nominees = []
    stats = {'total_coverage': 0, 'monthly_premium': 0, 'total_claims': 0}
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Fetch policies with their nominees and taken date
        cursor.execute("""
            SELECT p.*, pt.TAKEN_DATE, n.FNAME as N_FNAME, n.MNAME as N_MNAME, n.LNAME as N_LNAME, n.RELATION
            FROM policy p 
            JOIN policy_taken pt ON p.POLICY_ID = pt.POLICY_ID 
            LEFT JOIN nominee n ON p.POLICY_ID = n.POLICY_ID AND n.CUST_ID = %s
            WHERE pt.CUST_ID = %s
        """, (customer_id, customer_id))
        policies = cursor.fetchall()
        
        # Calculate stats and format duration
        for p in policies:
            stats['total_coverage'] += p['COV_AMT']
            stats['monthly_premium'] += p['PREM_AMT']
            # Convert DURATION to display format
            dur = format_duration(p['DURATION'])
            p['DURATION_DISPLAY'] = dur['text']
            p['DURATION_YEARS'] = dur['years']
            
            # Fetch latest claim for this policy
            cursor.execute("""
                SELECT cl.CLAIM_STATUS 
                FROM claim cl 
                JOIN cust_claim cc ON cl.CLAIM_ID = cc.CLAIM_ID 
                WHERE cc.POLICY_ID = %s 
                ORDER BY cl.CLAIM_DATE DESC LIMIT 1
            """, (p['POLICY_ID'],))
            latest_claim = cursor.fetchone()
            p['LATEST_CLAIM_STATUS'] = latest_claim['CLAIM_STATUS'] if latest_claim else None
            
            # Check if payment is done
            cursor.execute("""
                SELECT COUNT(*) as pay_count 
                FROM cust_pay cp 
                JOIN payment pay ON cp.PAY_ID = pay.PAY_ID 
                WHERE cp.CUST_ID = %s AND pay.POLICY_ID = %s
            """, (customer_id, p['POLICY_ID']))
            p['HAS_PAYMENT'] = cursor.fetchone()['pay_count'] > 0
            
            # Check Maturity based on TAKEN_DATE
            if p['TAKEN_DATE']:
                from datetime import datetime, timedelta
                # Use total_days from format_duration for accurate maturity
                end_date = p['TAKEN_DATE'] + timedelta(days=int(format_duration(p['DURATION'])['total_days']))
                p['IS_MATURE'] = datetime.now().date() >= end_date
            else:
                p['IS_MATURE'] = False
            
        # Fetch claims
        cursor.execute("""
            SELECT cl.*, p.POLICY_TYPE, p.POLICY_ID
            FROM claim cl 
            JOIN cust_claim cc ON cl.CLAIM_ID = cc.CLAIM_ID 
            JOIN policy p ON cc.POLICY_ID = p.POLICY_ID
            WHERE cc.CUST_ID = %s
        """, (customer_id,))
        claims = cursor.fetchall()
        stats['total_claims'] = len(claims)
        
        # Fetch all nominees (for the nominees tab)
        cursor.execute("SELECT * FROM nominee WHERE CUST_ID = %s", (customer_id,))
        nominees = cursor.fetchall()
        
        # Fetch payments
        cursor.execute("""
            SELECT pay.* FROM payment pay 
            JOIN cust_pay cp ON pay.PAY_ID = cp.PAY_ID 
            WHERE cp.CUST_ID = %s
        """, (customer_id,))
        payments = cursor.fetchall()
        
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Dashboard error: {e}")

    return render_template('customer-dashboard.html', 
                            customer_name=session['customer_name'],
                            policies=policies,
                            claims=claims,
                            payments=payments,
                            nominees=nominees,
                            stats=stats)

@app.route('/customer/policy/<policy_id>')
def policy_details(policy_id):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer_id = session['customer_id']
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Policy details with TAKEN_DATE
        cursor.execute("""
            SELECT p.*, pt.TAKEN_DATE 
            FROM policy p 
            JOIN policy_taken pt ON p.POLICY_ID = pt.POLICY_ID 
            WHERE p.POLICY_ID = %s AND pt.CUST_ID = %s
        """, (policy_id, customer_id))
        policy = cursor.fetchone()
        
        if policy:
            # Convert DURATION to display format
            dur = format_duration(policy['DURATION'])
            policy['DURATION_DISPLAY'] = dur['text']
            policy['DURATION_YEARS'] = dur['years']
            
            # Fetch latest claim for this policy
            cursor.execute("""
                SELECT cl.CLAIM_STATUS 
                FROM claim cl 
                JOIN cust_claim cc ON cl.CLAIM_ID = cc.CLAIM_ID 
                WHERE cc.POLICY_ID = %s 
                ORDER BY cl.CLAIM_DATE DESC LIMIT 1
            """, (policy_id,))
            latest_claim = cursor.fetchone()
            policy['LATEST_CLAIM_STATUS'] = latest_claim['CLAIM_STATUS'] if latest_claim else None
            
            # Check if payment is done
            cursor.execute("""
                SELECT COUNT(*) as pay_count 
                FROM cust_pay cp 
                JOIN payment pay ON cp.PAY_ID = pay.PAY_ID 
                WHERE cp.CUST_ID = %s AND pay.POLICY_ID = %s
            """, (customer_id, policy_id))
            policy['HAS_PAYMENT'] = cursor.fetchone()['pay_count'] > 0
            
            # Check Maturity based on TAKEN_DATE
            if policy['TAKEN_DATE']:
                from datetime import datetime, timedelta
                end_date = policy['TAKEN_DATE'] + timedelta(days=int(format_duration(policy['DURATION'])['total_days']))
                policy['IS_MATURE'] = datetime.now().date() >= end_date
                policy['END_DATE_FORMATTED'] = end_date.strftime('%Y-%m-%d')
            else:
                policy['IS_MATURE'] = False
                policy['END_DATE_FORMATTED'] = 'N/A'
                
        # Personal details
        cursor.execute("""
            SELECT c.*, e.EMAIL, ph.PHONE 
            FROM customer c 
            LEFT JOIN cust_email e ON c.CUST_ID = e.CUST_ID
            LEFT JOIN cust_phone ph ON c.CUST_ID = ph.CUST_ID
            WHERE c.CUST_ID = %s
        """, (customer_id,))
        customer = cursor.fetchone()
        
        # Nominee details
        cursor.execute("SELECT * FROM nominee WHERE CUST_ID = %s AND POLICY_ID = %s", (customer_id, policy_id))
        nominee = cursor.fetchone()
        
        # Payment details
        cursor.execute("SELECT * FROM payment WHERE POLICY_ID = %s AND PAY_ID IN (SELECT PAY_ID FROM cust_pay WHERE CUST_ID = %s)", (policy_id, customer_id))
        payments = cursor.fetchall()
        
        cursor.close()
        db.close()
        return render_template('policy_details.html', policy=policy, customer=customer, nominee=nominee, payments=payments)
    except Exception as e:
        return f"Error: {e}"

@app.route('/customer/claim/<policy_id>', methods=['GET', 'POST'])
def request_claim(policy_id):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    customer_id = session['customer_id']
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if policy already has a pending or successful claim BY THIS CUSTOMER
        cursor.execute("""
            SELECT cl.CLAIM_STATUS FROM claim cl
            JOIN cust_claim cc ON cl.CLAIM_ID = cc.CLAIM_ID
            WHERE cc.POLICY_ID = %s AND cc.CUST_ID = %s AND cl.CLAIM_STATUS IN ('Pending', 'Success')
        """, (policy_id, customer_id))
        existing_claim = cursor.fetchone()
        
        if existing_claim:
            # Cannot request again if already pending or success
            flash("A claim for this policy is already being processed or has been settled.", "info")
            cursor.close()
            db.close()
            return redirect(url_for('customer_dashboard'))

        # Check if policy duration has passed relative to TAKEN_DATE
        cursor.execute("""
            SELECT p.DURATION, p.COV_AMT, pt.TAKEN_DATE 
            FROM policy p 
            JOIN policy_taken pt ON p.POLICY_ID = pt.POLICY_ID 
            WHERE p.POLICY_ID = %s AND pt.CUST_ID = %s
        """, (policy_id, customer_id))
        policy = cursor.fetchone()
        
        # Check if payment exists
        cursor.execute("""
            SELECT COUNT(*) as pay_count 
            FROM cust_pay cp 
            JOIN payment pay ON cp.PAY_ID = pay.PAY_ID 
            WHERE cp.CUST_ID = %s AND pay.POLICY_ID = %s
        """, (customer_id, policy_id))
        has_payment = cursor.fetchone()['pay_count'] > 0

        if not has_payment:
            flash("You must make at least one payment before filing a claim.", "error")
            cursor.close()
            db.close()
            return redirect(url_for('customer_dashboard'))

        if policy and policy['TAKEN_DATE']:
            from datetime import datetime, timedelta
            # Use total_days from format_duration for accurate maturity
            dur_info = format_duration(policy['DURATION'])
            end_date = policy['TAKEN_DATE'] + timedelta(days=int(dur_info['total_days']))
            
            if datetime.now().date() >= end_date:
                # Only perform the insert if it's a POST or a deliberate action
                raw_uid = str(uuid.uuid4().int)
                short_uid = ""
                for i in range(min(6, len(raw_uid))):
                    short_uid += raw_uid[i]
                claim_id = f"CLM{short_uid}"
                
                cursor.execute(
                    "INSERT INTO claim (CLAIM_ID, CLAIM_AMT, CLAIM_DATE, CLAIM_STATUS) VALUES (%s, %s, CURDATE(), 'Pending')",
                    (claim_id, policy['COV_AMT'])
                )
                cursor.execute(
                    "INSERT INTO cust_claim (CLAIM_ID, POLICY_ID, CUST_ID) VALUES (%s, %s, %s)",
                    (claim_id, policy_id, customer_id)
                )
                db.commit()
                flash("Claim request submitted successfully! Status: Awaiting admin verification.", "success")
            else:
                flash(f"This policy has not matured yet. It will mature on {end_date.strftime('%Y-%m-%d')}.", "error")                
        else:
            flash("Policy not found or not taken by you.", "error")

        cursor.close()
        db.close()
    except Exception as e:
        print(f"Claim request error: {e}")
        flash(f"System error: {e}", "error")
        
    return redirect(url_for('customer_dashboard'))

@app.route('/customer/logout')
def customer_logout():
    session.clear()
    return redirect(url_for('customer_login'))

@app.route('/take_policy/<policy_id>', methods=['GET', 'POST'])
def take_policy(policy_id):
    # Check if a customer is logged in or an agent is acting for a customer
    target_cust_id = request.args.get('cust_id') or request.form.get('cust_id')
    
    if 'customer_id' not in session and 'agent_id' not in session:
        return redirect(url_for('customer_login', next=request.url))
    
    # If agent is logged in, they MUST provide a cust_id
    if 'agent_id' in session and not target_cust_id:
        return redirect(url_for('agent_dashboard'))
        
    # The ID we will use for the registration
    active_cust_id = target_cust_id if ('agent_id' in session) else session.get('customer_id')

    error = None
    success = None
    
    if request.method == 'POST':
        # Retrieve nominee details
        nominee_fname = request.form.get('nominee_fname', '').strip()
        nominee_mname = request.form.get('nominee_mname', '').strip()
        nominee_lname = request.form.get('nominee_lname', '').strip()
        nominee_relation = request.form.get('nominee_relation', '').strip()
        nominee_email = request.form.get('nominee_email', '').strip()
        nominee_phone = request.form.get('nominee_phone', '').strip()
        
        if not nominee_fname or not nominee_lname or not nominee_relation:
            error = "Nominee first name, last name, and relationship are required."
        else:
            try:
                db = get_db()
                cursor = db.cursor()
                
                # Insert Nominee
                raw_uid = str(uuid.uuid4().int)
                short_uid = ""
                for i in range(min(6, len(raw_uid))):
                    short_uid += raw_uid[i]
                nominee_id = f"NOM{short_uid}"
                cursor.execute(
                    "INSERT INTO nominee (NOMINEE_ID, FNAME, MNAME, LNAME, RELATION, CUST_ID, POLICY_ID) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (nominee_id, nominee_fname, nominee_mname, nominee_lname, nominee_relation, active_cust_id, policy_id)
                )
                
                if nominee_email:
                    cursor.execute("INSERT INTO nominee_email (NOMINEE_ID, EMAIL) VALUES (%s, %s)", (nominee_id, nominee_email))
                if nominee_phone:
                    cursor.execute("INSERT INTO nominee_phone (NOMINEE_ID, PHONE) VALUES (%s, %s)", (nominee_id, nominee_phone))
                
                cursor.execute("INSERT INTO cust_nominee (CUST_ID, NOMINEE_ID) VALUES (%s, %s)", (active_cust_id, nominee_id))
                
                # Check if policy explicitly already taken
                cursor.execute("SELECT * FROM policy_taken WHERE POLICY_ID = %s AND CUST_ID = %s", (policy_id, active_cust_id))
                if cursor.fetchone():
                    error = "You have already taken this policy."
                else:
                    # Take policy
                    cursor.execute(
                        "INSERT INTO policy_taken (POLICY_ID, CUST_ID, TAKEN_DATE) VALUES (%s, %s, CURDATE())",
                        (policy_id, active_cust_id)
                    )
                    db.commit()
                    success = "Policy taken successfully! Details stored."
                
                db.close()
                if success:
                    if 'agent_id' in session:
                        return redirect(url_for('agent_dashboard'))
                    return redirect(url_for('customer_dashboard'))
            except mysql.connector.Error as e:
                error = f"Database error: {e}"

    # Fetch policy info and customer info
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Fetch policy
        cursor.execute("SELECT * FROM policy WHERE POLICY_ID = %s", (policy_id,))
        policy = cursor.fetchone()
        if policy:
            dur = format_duration(policy['DURATION'])
            policy['DURATION_DISPLAY'] = dur['text']
            policy['DURATION_YEARS'] = dur['years']
        
        # Fetch customer info for auto-filling
        customer_id = active_cust_id
        cursor.execute("""
            SELECT c.*, e.EMAIL, p.PHONE 
            FROM customer c 
            LEFT JOIN cust_email e ON c.CUST_ID = e.CUST_ID 
            LEFT JOIN cust_phone p ON c.CUST_ID = p.CUST_ID 
            WHERE c.CUST_ID = %s
        """, (customer_id,))
        customer_info = cursor.fetchone()
        
        cursor.close()
        db.close()
    except Exception as e:
        policy = None
        customer_info = None
        error = f"Error fetching details: {e}"

    if not policy:
        return "Policy not found", 404

    return render_template('take_policy.html', 
                          policy=policy, 
                          customer_info=customer_info, 
                          error=error, 
                          success=success,
                          active_cust_id=active_cust_id)

# ─── Agent Routes ─────────────────────────────────────────────────────────────

@app.route('/agent/login', methods=['GET', 'POST'])
def agent_login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = "All fields are required."
        else:
            try:
                db = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    """
                    SELECT a.AGENT_ID, a.FNAME, a.MNAME, a.LNAME, a.PASSWORD 
                    FROM agent a
                    JOIN agent_email e ON a.AGENT_ID = e.AGENT_ID
                    WHERE e.EMAIL = %s
                    """,
                    (email,)
                )
                agent = cursor.fetchone()
                cursor.close()
                db.close()

                if agent and agent['PASSWORD'] == password:
                    session['agent_id'] = agent['AGENT_ID']
                    mname = agent['MNAME'] + " " if agent['MNAME'] else ""
                    session['agent_name'] = f"{agent['FNAME']} {mname}{agent['LNAME']}"
                    return redirect(url_for('agent_dashboard'))
                else:
                    error = "Invalid credentials. Please try again."
            except mysql.connector.Error as e:
                error = f"Database error: {e}"

    return render_template("agent-login.html", error=error)

@app.route('/agent/register', methods=['GET', 'POST'])
def agent_register():
    error = None
    if request.method == 'POST':
        fname = request.form.get('fname', '').strip()
        mname = request.form.get('mname', '').strip()
        lname = request.form.get('lname', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not all([fname, lname, phone, email, password]):
            error = "Please fill out all required fields."
        else:
            raw_uid = str(uuid.uuid4().int)
            short_uid = ""
            for i in range(min(6, len(raw_uid))):
                short_uid += raw_uid[i]
            agent_id = f"AGT{short_uid}"
            try:
                db = get_db()
                cursor = db.cursor()
                
                # Check if email exists
                cursor.execute("SELECT * FROM agent_email WHERE EMAIL = %s", (email,))
                if cursor.fetchone():
                    error = "An account with this email already exists."
                    cursor.close()
                    db.close()
                    return render_template("agent-register.html", error=error)

                # Insert into agent table
                cursor.execute(
                    """
                    INSERT INTO agent (AGENT_ID, FNAME, MNAME, LNAME, PASSWORD)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (agent_id, fname, mname, lname, password)
                )

                # Insert into agent_email
                cursor.execute(
                    "INSERT INTO agent_email (AGENT_ID, EMAIL) VALUES (%s, %s)",
                    (agent_id, email)
                )

                # Insert into agent_phone
                cursor.execute(
                    "INSERT INTO agent_phone (AGENT_ID, PHONE) VALUES (%s, %s)",
                    (agent_id, phone)
                )

                db.commit()
                cursor.close()
                db.close()

                return redirect(url_for('agent_login'))
            except mysql.connector.Error as e:
                error = f"Database error: {e}"

    return render_template("agent-register.html", error=error)

@app.route('/agent/dashboard')
def agent_dashboard():
    if 'agent_id' not in session:
        return redirect(url_for('agent_login'))
    
    agent_id = session['agent_id']
    clients = []
    claims = []
    stats = {'total_clients': 0, 'active_policies': 0}
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Fetch ALL customers linked to this agent via AGENT_CUST table
        cursor.execute("""
            SELECT DISTINCT
                c.CUST_ID, c.FNAME, c.MNAME, c.LNAME,
                e.EMAIL,
                ph.PHONE,
                p.POLICY_TYPE, p.POLICY_ID, p.PREM_AMT, p.DURATION,
                pt.TAKEN_DATE
            FROM agent_cust ac
            JOIN customer c ON ac.CUST_ID = c.CUST_ID
            LEFT JOIN policy_taken pt ON c.CUST_ID = pt.CUST_ID
            LEFT JOIN policy p ON pt.POLICY_ID = p.POLICY_ID
            LEFT JOIN cust_email e ON c.CUST_ID = e.CUST_ID
            LEFT JOIN cust_phone ph ON c.CUST_ID = ph.CUST_ID
            WHERE ac.AGENT_ID = %s
        """, (agent_id,))
        
        clients = cursor.fetchall()

        # Calculate stats
        total_clients_set = set()
        active_policies_count = 0
        
        for c in clients:
            total_clients_set.add(c['CUST_ID'])
            if c['POLICY_ID']:
                active_policies_count += 1
            
            dur = format_duration(c.get('DURATION'))
            c['DURATION_DISPLAY'] = dur['text']
            c['DURATION_YEARS'] = dur['years']
        
        stats = {
            'total_clients': len(total_clients_set),
            'active_policies': active_policies_count
        }

        # Fetch claims for all customers linked to this agent
        cursor.execute("""
            SELECT 
                cl.*, c.FNAME, c.MNAME, c.LNAME, p.POLICY_TYPE
            FROM claim cl
            JOIN cust_claim cc ON cl.CLAIM_ID = cc.CLAIM_ID
            JOIN policy_taken pt ON cc.POLICY_ID = pt.POLICY_ID
            JOIN customer c ON pt.CUST_ID = c.CUST_ID
            JOIN policy p ON pt.POLICY_ID = p.POLICY_ID
            WHERE c.CUST_ID IN (SELECT CUST_ID FROM agent_cust WHERE AGENT_ID = %s)
        """, (agent_id,))
        claims = cursor.fetchall()
            
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Agent Dashboard error: {e}")

    return render_template('agent-dashboard.html', 
                          agent_name=session['agent_name'],
                          clients=clients,
                          claims=claims,
                          stats=stats)

@app.route('/customer/pay/<policy_id>', methods=['GET', 'POST'])
def make_payment(policy_id):
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
    
    error = None
    customer_id = session['customer_id']
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        pay_mode = request.form.get('pay_mode', 'Online')
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Generate PAY_ID
            raw_uid = str(uuid.uuid4().int)
            short_uid = ""
            for i in range(min(6, len(raw_uid))):
                short_uid += raw_uid[i]
            pay_id = f"PAY{short_uid}"
            
            # Insert into payment
            cursor.execute(
                "INSERT INTO payment (PAY_ID, AMOUNT, PAY_MODE, PAY_DATE, POLICY_ID) VALUES (%s, %s, %s, CURDATE(), %s)",
                (pay_id, amount, pay_mode, policy_id)
            )
            
            # Insert into cust_pay
            cursor.execute(
                "INSERT INTO cust_pay (CUST_ID, PAY_ID) VALUES (%s, %s)",
                (customer_id, pay_id)
            )

            # Link payment to a default admin for verification
            cursor.execute(
                "INSERT INTO admin_verify_pay (ADMIN_ID, PAY_ID) VALUES (%s, %s)",
                ('ADMIN-001', pay_id)
            )
            
            db.commit()
            cursor.close()
            db.close()
            return redirect(url_for('customer_dashboard'))
        except mysql.connector.Error as e:
            error = f"Payment error: {e}"

    # Fetch policy info for the payment page
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM policy WHERE POLICY_ID = %s", (policy_id,))
        policy = cursor.fetchone()
        cursor.close()
        db.close()
    except Exception as e:
        policy = None
        error = f"Error fetching policy: {e}"

    return render_template('make_payment.html', policy=policy, error=error)

@app.route('/agent/logout')
def agent_logout():
    session.clear()
    return redirect(url_for('agent_login'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
