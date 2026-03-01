from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'supersecretkey'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root123'  # change this to your MySQL password
app.config['MYSQL_DB'] = 'flaskdb'

mysql = MySQL(app)


# -------------------- HOME --------------------
@app.route('/')
def home():
    return render_template('index.html')


# -------------------- CUSTOMER REGISTER --------------------
@app.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    # Auto generate next customer ID
    cur = mysql.connection.cursor()
    cur.execute("SELECT MAX(CAST(SUBSTRING(CUST_ID, 2) AS UNSIGNED)) FROM customer")
    result = cur.fetchone()[0]
    next_num = (result or 0) + 1
    next_id = "C{:03d}".format(next_num)
    cur.close()

    if request.method == 'POST':
        customer_id = request.form['customer_id']
        fname = request.form['fname']
        mname = request.form['mname']
        lname = request.form['lname']
        dob = request.form['dob']
        per_address = request.form['per_address']
        comm_address = request.form['comm_address']
        password = request.form['password']
        phone = request.form['phone']
        email = request.form['email']

        cur = mysql.connection.cursor()

        # Check if customer ID already exists
        cur.execute("SELECT * FROM customer WHERE CUST_ID=%s", (customer_id,))
        existing = cur.fetchone()

        if existing:
            return render_template('customer_register.html',
                                   next_id=next_id,
                                   error='Customer ID already exists. Please try again.')

        # Insert into customer table
        cur.execute("""INSERT INTO customer
                    (CUST_ID, FNAME, MNAME, LNAME, DOB, PER_ADDR, COMM_ADDR, PASSWORD)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (customer_id, fname, mname, lname, dob,
                     per_address, comm_address, password))

        # Insert phone
        cur.execute("INSERT INTO cust_phone (CUST_ID, PHONE) VALUES (%s,%s)",
                    (customer_id, phone))

        # Insert email
        cur.execute("INSERT INTO cust_email (CUST_ID, EMAIL) VALUES (%s,%s)",
                    (customer_id, email))

        mysql.connection.commit()
        cur.close()
        return redirect(url_for('home'))

    return render_template('customer_register.html', next_id=next_id)


# -------------------- CUSTOMER LOGIN --------------------
@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM customer WHERE CUST_ID=%s AND PASSWORD=%s",
                    (customer_id, password))
        customer = cur.fetchone()
        cur.close()

        if customer:
            session['customer_id'] = customer_id
            session['customer_name'] = customer[1]
            return redirect(url_for('customer_dashboard'))
        else:
            return render_template('index.html', error='Invalid Customer ID or Password')

    return redirect(url_for('home'))


# -------------------- CUSTOMER DASHBOARD --------------------
@app.route('/customer/dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('home'))

    customer_id = session['customer_id']
    cur = mysql.connection.cursor()

    # Customer details
    cur.execute("SELECT * FROM customer WHERE CUST_ID=%s", (customer_id,))
    customer = cur.fetchone()

    # Customer phone
    cur.execute("SELECT PHONE FROM cust_phone WHERE CUST_ID=%s", (customer_id,))
    phone = cur.fetchone()

    # Customer email
    cur.execute("SELECT EMAIL FROM cust_email WHERE CUST_ID=%s", (customer_id,))
    email = cur.fetchone()

    # Policies taken by customer
    cur.execute("""SELECT p.POLICY_ID, p.POLICY_TYPE, p.START_DATE,
                p.PREM_AMT, p.COV_AMT, p.STATUS
                FROM policy p
                JOIN policy_taken pt ON p.POLICY_ID = pt.POLICY_ID
                WHERE pt.CUST_ID=%s""", (customer_id,))
    policies = cur.fetchall()

    # Claims filed by customer
    cur.execute("""SELECT c.CLAIM_ID, c.CLAIM_AMT, c.CLAIM_DATE, c.CLAIM_STATUS
                FROM claim c
                JOIN cust_claim cc ON c.CLAIM_ID = cc.CLAIM_ID
                WHERE cc.POLICY_ID IN (
                    SELECT POLICY_ID FROM policy_taken WHERE CUST_ID=%s
                )""", (customer_id,))
    claims = cur.fetchall()

    # Payments made by customer
    cur.execute("""SELECT p.PAY_ID, p.AMOUNT, p.PAY_MODE, p.PAY_DATE
                FROM payment p
                JOIN cust_pay cp ON p.PAY_ID = cp.PAY_ID
                WHERE cp.CUST_ID=%s""", (customer_id,))
    payments = cur.fetchall()

    cur.close()
    return render_template('customer_dashboard.html',
                           customer=customer,
                           phone=phone,
                           email=email,
                           policies=policies,
                           claims=claims,
                           payments=payments)


# -------------------- LOGOUT --------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)