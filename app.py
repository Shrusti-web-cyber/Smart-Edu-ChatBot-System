import os, sqlite3, json, urllib.request, random, smtplib, io
from pathlib import Path
import ssl
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass
from email.message import EmailMessage
from datetime import date 
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from college_seed import COLLEGES
import smtplib
import ollama
import secrets
import urllib.error

AI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = "gpt-4.1-mini"

def generate_otp():
    return str(secrets.randbelow(900000) + 100000)


import smtplib
import ssl

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

env_path=Path(__file__).resolve().parent / ".env"

print("ENV FILE EXISTS:" , env_path.is_file())

import smtplib
import ssl

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

env_path=Path(__file__).resolve().parent / ".env"

print("ENV FILE EXISTS:" , env_path.is_file())

load_dotenv(dotenv_path=env_path, override=True)

print("SECRET KEY:", bool(os.getenv("SMARTEDU_SECRET")))
print("OPENAI API KEY:", bool(os.getenv("OPENAI_API_KEY")))
print("SMTP HOST:", bool(os.getenv("SMTP_HOST")))
print("SMTP USER:", bool(os.getenv("SMTP_USER")))
print("SMTP PASSWORD:", bool(os.getenv("SMTP_PASSWORD")))

app = Flask(__name__)
import os

print("APP FILE:", os.path.abspath(__file__))

template_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "templates",
    "faculty_dashboard.html"
)

print("TEMPLATE PATH:", template_path)
print("FILE EXISTS:", os.path.isfile(template_path))
app.secret_key = os.getenv('SMARTEDU_SECRET', 'change-this-secret')
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'smart_edu.db')
UPLOADS = os.path.join(BASE, 'uploads')
os.makedirs(UPLOADS, exist_ok=True)
ALLOWED = {'pdf','doc','docx','ppt','pptx','xls','xlsx','txt','jpg','jpeg','png','gif','webp','csv','mp3','wav','m4a','mp4','webm','mov'}
AI_API_KEY = os.getenv('OPENAI_API_KEY', '')
AI_MODEL = os.getenv('SMARTEDU_AI_MODEL', 'gpt-4.1-mini')
print("AI KEY LOADED:", bool(AI_API_KEY))
print("AI MODEL:", AI_MODEL)

BRANCHES = [('AI','Artificial Intelligence & Machine Learning'),('CS','Computer Science & Engineering'),('EC','Electronics & Communication Engineering'),('ME','Mechanical Engineering'),('CV','Civil Engineering'),('EE','Electrical & Electronics Engineering')]

def get_db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init_db():
    c = get_db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS colleges(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, district TEXT, app_code TEXT);
    CREATE TABLE IF NOT EXISTS timetable (id INTEGER PRIMARY KEY AUTOINCREMENT,college_id INTEGER NOT NULL,branch TEXT NOT NULL,semester INTEGER NOT NULL,day TEXT NOT NULL,start_time TEXT NOT NULL,end_time TEXT NOT NULL,subject TEXT NOT NULL,faculty TEXT,room TEXT);
    CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT, usn TEXT NOT NULL, branch TEXT, semester INTEGER, password TEXT, college_id INTEGER NOT NULL, UNIQUE(college_id,usn), FOREIGN KEY(college_id) REFERENCES colleges(id));
    CREATE TABLE IF NOT EXISTS faculty(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, password TEXT NOT NULL, mobile TEXT, email TEXT, branch TEXT, semester INTEGER, college_id INTEGER NOT NULL, UNIQUE(college_id,name), FOREIGN KEY(college_id) REFERENCES colleges(id));
    CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, subject TEXT NOT NULL, class_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Present','Absent')), UNIQUE(student_id,subject,class_date), FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS marks(id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, subject TEXT NOT NULL, ia1 REAL DEFAULT 0, ia2 REAL DEFAULT 0, ia3 REAL DEFAULT 0, assignment REAL DEFAULT 0, UNIQUE(student_id,subject), FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, subject TEXT, filename TEXT NOT NULL, file_type TEXT, uploaded_on TEXT, college_id INTEGER NOT NULL, FOREIGN KEY(college_id) REFERENCES colleges(id));
    CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, message TEXT NOT NULL, audience TEXT DEFAULT 'all', student_id INTEGER, created_at TEXT, college_id INTEGER NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE, FOREIGN KEY(college_id) REFERENCES colleges(id));
    CREATE TABLE IF NOT EXISTS email_otps(id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, role TEXT NOT NULL, otp_hash TEXT NOT NULL, payload TEXT NOT NULL, expires_at INTEGER NOT NULL, verified INTEGER DEFAULT 0);
    ''')
    timetable_cols = [
    r['name'] for r in
    c.execute ('PRAGMA table_info(timetable)').fetchall()
    ]

    if 'subject_code' not in timetable_cols:
        c.execute(
            'ALTER TABLE timetable ADD COLUMN subject_code TEXT'
        )
    
    for table, col, typ in [('students','mobile','TEXT'),('faculty','email','TEXT'),('faculty','branch','TEXT'),('faculty','semester','INTEGER')]:
        cols=[r['name'] for r in c.execute(f'PRAGMA table_info({table})').fetchall()]
        if col not in cols: c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {typ}')
    # Backward-compatible migration for the human-friendly college code (e.g. EE001).
    college_cols=[r['name'] for r in c.execute('PRAGMA table_info(colleges)').fetchall()]
    if 'app_code' not in college_cols: c.execute('ALTER TABLE colleges ADD COLUMN app_code TEXT')
    # Seed public institution catalog.
    for code,name,district in COLLEGES:
        c.execute('INSERT OR IGNORE INTO colleges(code,name,district) VALUES(?,?,?)',(code,name,district))
    # A clearly labelled demo college keeps first-run testing easy.
    c.execute('INSERT OR IGNORE INTO colleges(code,name,district) VALUES(?,?,?)',('DEMO','Demo College','Demo'))
    # Give every college a stable SmartEdu-facing code such as EE001, EE002...
    for idx,row in enumerate(c.execute('SELECT id FROM colleges ORDER BY id').fetchall(),1):
        c.execute('UPDATE colleges SET app_code=? WHERE id=? AND (app_code IS NULL OR app_code="")',(f'EE{idx:03d}',row['id']))
    demo_college = c.execute('SELECT id FROM colleges WHERE code=?',('DEMO',)).fetchone()['id']
    # Seed synthetic students: never claim these are real students.
    total = c.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    if total == 0:
        colleges = c.execute('SELECT id,code,name FROM colleges ORDER BY id').fetchall()
        names = ['Aarav Kumar','Ananya Patil','Rahul Shetty','Sneha Rao','Vivek Gowda']
        sid_rows=[]
        for col in colleges:
            for i in range(1,4):
                name = 'Shrusti' if col['id']==demo_college and i==1 else f'{names[(i-1)%len(names)]} {col["code"]}'
                branch_code, branch_name = BRANCHES[(i-1)%len(BRANCHES)]
                usn = f'1{col["code"][:2].upper():<2}{22:02d}{branch_code}{i:03d}'.replace(' ','0')
                email = f'demo.{col["code"].lower()}.{i}@smartedu.local'
                if col['id']==demo_college and i==1: usn='1BK22AI001'; branch_code='AI'; name='Shrusti'
                cur = c.execute('INSERT INTO students(name,email,usn,branch,semester,password,college_id,mobile) VALUES(?,?,?,?,?,?,?,?)',(name, email, usn, branch_code, 7, 'student123', col['id'], ''))
                sid_rows.append((cur.lastrowid,col['id'],branch_code))
        # Give each synthetic student small, realistic-looking demo academic data.
        subjects=['Machine Learning','Cloud Computing','Database Management','Web Technology']
        for sid,cid,bcode in sid_rows:
            for j,sub in enumerate(subjects):
                for d,status in [('01','Present'),('02','Present'),('03','Absent'),('04','Present'),('05','Present')]:
                    c.execute('INSERT OR IGNORE INTO attendance(student_id,subject,class_date,status) VALUES(?,?,?,?)',(sid,sub,f'2026-09-{d}',status if (j+d.__len__())%5 else 'Present'))
                c.execute('INSERT INTO marks(student_id,subject,ia1,ia2,ia3,assignment) VALUES(?,?,?,?,?,?)',(sid,sub,20+j,22+j,21+j,5))
    # One uniquely named admin account per college for demo/testing.
    # Login intentionally uses only admin name + password, so names must be globally unique.
    for col in c.execute('SELECT id,app_code FROM colleges ORDER BY id').fetchall():
        demo_admin_name = f"Admin-{col['app_code']}"
        has_admin=c.execute('SELECT id FROM faculty WHERE college_id=? LIMIT 1',(col['id'],)).fetchone()
        if not has_admin:
            c.execute('INSERT INTO faculty(name,password,mobile,email,branch,semester,college_id) VALUES(?,?,?,?,?,?,?)',(demo_admin_name,'admin123','',f'{demo_admin_name.lower().replace(" ",".")}@smartedu.local','AI',7,col['id']))
    # Upgrade older seeded rows that used the same generic name in every college.
    dupes=c.execute('SELECT name FROM faculty GROUP BY lower(name) HAVING COUNT(*)>1').fetchall()
    for d in dupes:
        rows=c.execute('SELECT f.id,c.app_code FROM faculty f JOIN colleges c ON c.id=f.college_id WHERE lower(f.name)=lower(?) ORDER BY f.id',(d['name'],)).fetchall()
        for r in rows:
            c.execute('UPDATE faculty SET name=? WHERE id=?',(f"Admin-{r['app_code']}",r['id']))
    # Expand the demo college to a realistic class size for admin-table demonstrations.
    demo_count=c.execute('SELECT COUNT(*) FROM students WHERE college_id=?',(demo_college,)).fetchone()[0]
    if demo_count < 200:
        subjects=['Machine Learning','Cloud Computing','Database Management','Web Technology','Computer Networks']
        for i in range(demo_count+1,201):
            name=f'Demo Student {i:03d}'; usn=f'1BK22AI{i:03d}'; email=f'demo.student{i:03d}@smartedu.local'
            try:
                cur=c.execute('INSERT INTO students(name,email,usn,branch,semester,password,college_id,mobile) VALUES(?,?,?,?,?,?,?,?)',(name,email,usn,'AI',7,'student123',demo_college,'9000000000'))
                sid=cur.lastrowid
                for j,sub in enumerate(subjects):
                    for d,status in [('01','Present'),('02','Present'),('03','Absent'),('04','Present'),('05','Present')]:
                        c.execute('INSERT OR IGNORE INTO attendance(student_id,subject,class_date,status) VALUES(?,?,?,?)',(sid,sub,f'2026-09-{d}',status))
                    c.execute('INSERT OR IGNORE INTO marks(student_id,subject,ia1,ia2,ia3,assignment) VALUES(?,?,?,?,?,?)',(sid,sub,18+j%4,20+j%3,19+j%5,5))
            except sqlite3.IntegrityError:
                pass

    if c.execute('SELECT COUNT(*) FROM notifications').fetchone()[0] == 0:
        c.execute('INSERT INTO notifications(title,message,audience,created_at,college_id) VALUES(?,?,?,?,?)',('Welcome to Smart Edu','This is a synthetic demo notification.','all',date.today().isoformat(),demo_college))
    c.commit(); c.close()

def student():
    sid=session.get('student_id')
    if not sid:return None
    c=get_db(); x=c.execute('SELECT s.*, c.name college_name, c.code college_code, c.app_code college_app_code, c.district FROM students s JOIN colleges c ON c.id=s.college_id WHERE s.id=?',(sid,)).fetchone(); c.close(); return x

def faculty():
    fid=session.get('faculty_id')
    if not fid:return None
    c=get_db(); x=c.execute('SELECT f.*,c.name college_name,c.code college_code,c.app_code college_app_code FROM faculty f JOIN colleges c ON c.id=f.college_id WHERE f.id=?',(fid,)).fetchone(); c.close(); return x

def colleges():
    c=get_db(); rows=c.execute('SELECT * FROM colleges ORDER BY name').fetchall(); c.close(); return rows

def send_otp_email(email, otp, role):
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = "".join(
        os.getenv("SMTP_PASSWORD", "").split()
    )
    sender = os.getenv("SMTP_FROM", "").strip()

    if not all([host, user, password, sender]):
        raise RuntimeError("SMTP settings are missing in .env")

    msg = EmailMessage()
    msg["Subject"] = "SmartEdu email verification OTP"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(
        f"Your SmartEdu {role} verification OTP is {otp}. "
        "It expires in 10 minutes. Do not share this code."
    )

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls(
                context=ssl.create_default_context()
            )
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)

        print("OTP EMAIL SENT")

    except Exception as e:
        print("OTP EMAIL ERROR:", type(e).__name__, str(e))
        raise
    

def create_otp(role, payload):
    email=payload['email'].lower().strip(); otp=f'{random.randint(0,999999):06d}'
    import hashlib, time
    otp_hash=hashlib.sha256(otp.encode()).hexdigest(); expires=int(time.time())+600
    c=get_db(); c.execute('DELETE FROM email_otps WHERE email=? AND role=?',(email,role)); c.execute('INSERT INTO email_otps(email,role,otp_hash,payload,expires_at) VALUES(?,?,?,?,?)',(email,role,otp_hash,json.dumps(payload),expires)); c.commit(); c.close()
    send_otp_email(email,otp,role)
    print("OTP EMAIL FUNCTION CALLED")

def verify_otp(email, role, otp):
    import hashlib, time
    c=get_db(); row=c.execute('SELECT * FROM email_otps WHERE email=? AND role=? AND verified=0 ORDER BY id DESC LIMIT 1',(email.lower().strip(),role)).fetchone()
    if not row or int(row['expires_at']) < int(time.time()): c.close(); return None
    if hashlib.sha256(otp.strip().encode()).hexdigest()!=row['otp_hash']: c.close(); return None
    payload=json.loads(row['payload']); c.execute('DELETE FROM email_otps WHERE id=?',(row['id'],)); c.commit(); c.close(); return payload

def password_ok(stored, supplied):
    try: return check_password_hash(stored,supplied)
    except Exception: return stored==supplied

def attendance_for(sid):
    c=get_db(); rows=c.execute("""SELECT subject,SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) present,COUNT(*) total FROM attendance WHERE student_id=? GROUP BY subject ORDER BY subject""",(sid,)).fetchall(); c.close()
    return [{'subject':r['subject'],'present':r['present'],'total':r['total'],'pct':round(r['present']/r['total']*100,1) if r['total'] else 0} for r in rows]

def overall_attendance(sid):
    rows=attendance_for(sid); p=sum(x['present'] for x in rows); t=sum(x['total'] for x in rows); return round(p/t*100,1) if t else 0

def same_college_student(sid, college_id):
    c=get_db(); x=c.execute('SELECT id FROM students WHERE id=? AND college_id=?',(sid,college_id)).fetchone(); c.close(); return bool(x)

@app.route('/')
def home():
    if student(): return redirect(url_for('dashboard'))
    if faculty(): return redirect(url_for('faculty_dashboard'))
    return render_template('landing.html')

@app.route('/login-choice')
def login_choice():
    if student(): return redirect(url_for('dashboard'))
    if faculty(): return redirect(url_for('faculty_dashboard'))
    return render_template('login_choice.html')

@app.route('/login')
def login():
    if student(): return redirect(url_for('dashboard'))
    if faculty(): return redirect(url_for('faculty_dashboard'))
    return render_template('login.html')

@app.route('/signup')
def signup_choice():
    # Signup remains available through its dedicated setup URLs, but no signup option is shown in the public UI.
    return redirect(url_for('home'))

@app.route('/signup/send-otp', methods=['POST'])
def signup_send_otp():
    print("SEND OTP ROUTE REACHED")
    """Send a fresh OTP to exactly the email entered in the signup form.
    Any previous OTP for the same email/role is deleted first.
    """
    role=request.form.get('role','').strip().lower()
    email=request.form.get('email','').strip().lower()
    if role not in ('student','admin'):
        return jsonify(ok=False, message='Invalid signup role.'), 400
    import re
    if not re.fullmatch(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', email):
        return jsonify(ok=False, message='Enter a valid email address.'), 400
    c=get_db()
    table='students' if role=='student' else 'faculty'
    exists=c.execute(f'SELECT id FROM {table} WHERE lower(email)=lower(?)',(email,)).fetchone()
    c.close()
    if exists:
        return jsonify(ok=False, message='This email is already registered.'), 409
    try:
        create_otp(role, {'email':email})
        session['signup_otp_email']=email
        session['signup_otp_role']=role
        session['signup_email_verified']=False
        return jsonify(ok=True, message='OTP sent. Check that email inbox.' )
    
    except Exception as e:
        app.logger.exception("OTP email sending failed")
        print("OTP EMAIL ERROR:", type(e).__name__, str(e))
        print("OTP ERROR:", repr(e))
        return jsonify(
            ok=False,
            message="Could not send verification code. Please try again."
        ), 500

@app.route('/signup/verify-otp', methods=['POST'])
def signup_verify_otp():
    role=request.form.get('role','').strip().lower()
    email=request.form.get('email','').strip().lower()
    otp=request.form.get('otp','').strip()
    if email != session.get('signup_otp_email') or role != session.get('signup_otp_role'):
        return jsonify(ok=False, message='Please send a new OTP for this email.'), 400
    payload=verify_otp(email, role, otp)
    if not payload:
        session['signup_email_verified']=False
        return jsonify(ok=False, message='Wrong or expired OTP.'), 400
    session['signup_email_verified']=True
    return jsonify(ok=True, message='Email verified successfully.')

@app.route('/signup/student', methods=['GET','POST'])
def student_signup():
    if request.method=='POST':
        data={k:request.form.get(k,'').strip() for k in ['name','college_id','email','mobile','usn','branch','semester']}
        data['email']=data['email'].lower()
        pw=request.form.get('password',''); cpw=request.form.get('confirm_password','')
        if session.get('signup_email_verified') is not True or session.get('signup_otp_role')!='student' or session.get('signup_otp_email')!=data['email']:
            flash('Please verify this email with the OTP first.'); return render_template('student_signup.html', colleges=colleges(), branches=BRANCHES)
        if pw!=cpw or len(pw)<6: flash('Passwords must match and be at least 6 characters.'); return render_template('student_signup.html', colleges=colleges(), branches=BRANCHES)
        try: cid=int(data['college_id'])
        except ValueError: flash('Select a valid college.'); return render_template('student_signup.html', colleges=colleges(), branches=BRANCHES)
        c=get_db(); exists=c.execute('SELECT id FROM students WHERE college_id=? AND upper(usn)=upper(?)',(cid,data['usn'])).fetchone(); email_exists=c.execute('SELECT id FROM students WHERE lower(email)=lower(?)',(data['email'],)).fetchone(); c.close()
        if exists: flash('That USN is already registered in this college.'); return render_template('student_signup.html', colleges=colleges(), branches=BRANCHES)
        if email_exists: flash('That email is already registered.'); return render_template('student_signup.html', colleges=colleges(), branches=BRANCHES)
        c=get_db()
        try:
            c.execute('INSERT INTO students(name,email,usn,branch,semester,password,college_id,mobile) VALUES(?,?,?,?,?,?,?,?)',(data['name'],data['email'],data['usn'],data['branch'],int(data.get('semester') or 1),generate_password_hash(pw),cid,data.get('mobile','')))
            c.commit(); c.close()
        except sqlite3.IntegrityError:
            c.close(); flash('This account could not be created because the name/USN/email is already registered.'); return render_template('student_signup.html', colleges=colleges(), branches=BRANCHES)
        for k in ('signup_otp_email','signup_otp_role','signup_email_verified'): session.pop(k,None)
        flash('Student account created. Your email is verified. You can now login.'); return redirect(url_for('student_login'))
    return render_template('student_signup.html', colleges=colleges(), branches=BRANCHES)

@app.route('/signup/admin', methods=['GET','POST'])
def admin_signup():
    if request.method=='POST':
        data={k:request.form.get(k,'').strip() for k in ['name','email','mobile','college_id','branch','semester']}
        data['email']=data['email'].lower()
        pw=request.form.get('password',''); cpw=request.form.get('confirm_password','')
        if session.get('signup_email_verified') is not True or session.get('signup_otp_role')!='admin' or session.get('signup_otp_email')!=data['email']:
            flash('Please verify this email with the OTP first.'); return render_template('admin_signup.html', colleges=colleges(), branches=BRANCHES)
        if pw!=cpw or len(pw)<6: flash('Passwords must match and be at least 6 characters.'); return render_template('admin_signup.html', colleges=colleges(), branches=BRANCHES)
        try: cid=int(data['college_id'])
        except ValueError: flash('Select a valid college.'); return render_template('admin_signup.html', colleges=colleges(), branches=BRANCHES)
        c=get_db(); exists=c.execute('SELECT id FROM faculty WHERE lower(name)=lower(?)',(data['name'],)).fetchone(); email_exists=c.execute('SELECT id FROM faculty WHERE lower(email)=lower(?)',(data['email'],)).fetchone(); c.close()
        if exists: flash('That admin name is already in use. Please choose a unique admin name.'); return render_template('admin_signup.html', colleges=colleges(), branches=BRANCHES)
        if email_exists: flash('That admin email is already registered.'); return render_template('admin_signup.html', colleges=colleges(), branches=BRANCHES)
        c=get_db()
        try:
            c.execute('INSERT INTO faculty(name,password,mobile,email,branch,semester,college_id) VALUES(?,?,?,?,?,?,?)',(data['name'],generate_password_hash(pw),data['mobile'],data['email'],data['branch'],int(data.get('semester') or 1),cid))
            c.commit(); c.close()
        except sqlite3.IntegrityError:
            c.close(); flash('This admin account could not be created because the email/name is already registered.'); return render_template('admin_signup.html', colleges=colleges(), branches=BRANCHES)
        for k in ('signup_otp_email','signup_otp_role','signup_email_verified'): session.pop(k,None)
        flash('Admin account created. Your email is verified. You can now login.'); return redirect(url_for('faculty_login'))
    return render_template('admin_signup.html', colleges=colleges(), branches=BRANCHES)

@app.route('/student-login', methods=['GET','POST'])
def student_login():
    if request.method=='POST':
        name=request.form.get('name','').strip(); usn=request.form.get('usn','').strip().upper(); pw=request.form.get('password','')
        c=get_db(); matches=c.execute('SELECT * FROM students WHERE lower(name)=lower(?) AND upper(usn)=?',(name,usn)).fetchall(); c.close()
        s=matches[0] if len(matches)==1 else None
        if s and password_ok(s['password'],pw):
            session.clear(); session['student_id']=s['id']; session['student_role']='student'; return redirect(url_for('dashboard'))
        flash('Student name, USN or password is incorrect.')
    return render_template('student_login.html')

@app.route('/faculty-login', methods=['GET','POST'])
def faculty_login():
    if request.method=='POST':
        name=request.form.get('name','').strip(); pw=request.form.get('password','')
        c=get_db(); matches=c.execute('SELECT * FROM faculty WHERE lower(name)=lower(?)',(name,)).fetchall(); c.close()
        f=matches[0] if len(matches)==1 else None
        if f and password_ok(f['password'],pw):
            session.clear(); session['faculty_id']=f['id']; session['admin_role']='admin'; return redirect(url_for('faculty_dashboard'))
        flash('Admin name or password is incorrect.')
    return render_template('faculty_login.html')

@app.route('/logout')
def logout():
    was_student=bool(session.get('student_id'))
    was_admin=bool(session.get('faculty_id'))
    session.clear()
    if was_student: return redirect(url_for('student_login'))
    if was_admin: return redirect(url_for('faculty_login'))
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    s=student()
    if not s:return redirect(url_for('student_login'))
    c=get_db(); marks=c.execute('SELECT * FROM marks WHERE student_id=? ORDER BY subject',(s['id'],)).fetchall(); mats=c.execute('SELECT * FROM materials WHERE college_id=? ORDER BY id DESC LIMIT 8',(s['college_id'],)).fetchall(); notifications=c.execute("SELECT * FROM notifications WHERE college_id=? AND (audience IN ('all','students') OR student_id=?) ORDER BY id DESC LIMIT 8",(s['college_id'],s['id'])).fetchall(); c.close()
    return render_template('dashboard.html',student=s,rows=attendance_for(s['id']),overall=overall_attendance(s['id']),marks=marks,mats=mats,notifications=notifications)

@app.route('/attendance')
def attendance():
    s=student()
    if not s:return redirect(url_for('student_login'))
    return render_template('attendance.html',rows=attendance_for(s['id']),overall=overall_attendance(s['id']))

@app.route('/marks')
def marks():
    s=student()
    if not s:return redirect(url_for('student_login'))
    c=get_db(); rows=c.execute('SELECT * FROM marks WHERE student_id=? ORDER BY subject',(s['id'],)).fetchall(); c.close(); return render_template('marks.html',rows=rows)

@app.route('/materials')
def materials():
    s=student()
    if not s:return redirect(url_for('student_login'))
    c=get_db(); rows=c.execute('SELECT * FROM materials WHERE college_id=? ORDER BY id DESC',(s['college_id'],)).fetchall(); c.close(); return render_template('materials.html',rows=rows)

@app.route('/download/<path:filename>')
def download(filename):
    s=student(); f=faculty()
    if not s and not f:return redirect(url_for('home'))
    c=get_db(); row=c.execute('SELECT college_id FROM materials WHERE filename=?',(filename,)).fetchone(); c.close()
    if not row:return 'File not found',404
    if os.path.basename(filename) != filename:return 'Invalid file name',400
    if s and row['college_id']!=s['college_id']:return 'Not authorized',403
    if f and row['college_id']!=f['college_id']:return 'Not authorized',403
    return send_from_directory(UPLOADS,filename,as_attachment=True)

@app.route('/planner')
def planner():
    s=student()
    if not s:return redirect(url_for('student_login'))
    return render_template('planner.html',student=s)

@app.route('/quiz')
def quiz():
    s=student()
    if not s:return redirect(url_for('student_login'))
    return render_template('quiz.html',student=s)

@app.route('/result')
def result():
    s=student()
    if not s:return redirect(url_for('student_login'))
    c=get_db(); rows=c.execute('SELECT * FROM marks WHERE student_id=? ORDER BY subject',(s['id'],)).fetchall(); c.close()
    return render_template('result.html',student=s,rows=rows)

@app.route('/timetable')
def timetable():
    s = student()
    if not s:
        return redirect(url_for('student_login'))

    c = get_db()
    try:
        rows = c.execute(
            '''SELECT day, start_time, end_time, subject, faculty, room
               FROM timetable
               WHERE college_id = ? AND branch = ? AND semester = ?
               ORDER BY day, start_time''',
            (s['college_id'], s['branch'], s['semester'])
        ).fetchall()
    finally:
        c.close()

    return render_template(
        'timetable.html',
        student=s,
        timetable=rows
    )


@app.route('/college-info')
def college_info():
    s=student()
    if not s:return redirect(url_for('student_login'))
    return render_template('college_info.html',student=s)

@app.route('/chatbot')
def chatbot():
    if not student():return redirect(url_for('student_login'))
    return render_template('chatbot.html')

@app.route('/api/chat',methods=['POST'])
def chat():
    s=student()
    if not s:return jsonify({'answer':'Please log in first.'}),401
    payload=request.json or {}
    q=str(payload.get('message','')).strip()
    history=payload.get('history') or []
    if not q:return jsonify({'answer':'Please type a question.'})
    
    if AI_API_KEY:
        try:
            return jsonify({
                'answer': call_ai(q, s, history),
                'mode': 'AI'
            })
        

        except Exception as exc:
            print("SMARTEDU AI ERROR:", repr(exc), flush=True)

            if isinstance(exc, urllib.error.HTTPError):
                print("HTTP STATUS:", exc.code, flush=True)
                print(
                    "API ERROR DETAILS:",
                    exc.read().decode("utf-8", "replace"),
                    flush=True
                )

            app.logger.exception("SmartEdu AI provider request failed")

            return jsonify({
                'answer': 'The AI service failed. Check the VS Code terminal for the exact error.',
                'mode': 'error'
            }), 502

    return jsonify({
        'answer': smart_local_answer(q, s['id']),
        'mode': 'local',
        'setup_required': True
    })


def call_ai(q, s, history=None):
    c = get_db()
    try:
        m = c.execute(
            'SELECT subject,ia1,ia2,ia3,assignment FROM marks WHERE student_id=?',
            (s['id'],)
        ).fetchall()
        mats = c.execute(
            'SELECT title,subject,file_type FROM materials WHERE college_id=?',
            (s['college_id'],)
        ).fetchall()
    finally:
        c.close()

    context = {
        'student': {
            'name': s['name'],
            'college': s['college_name'],
            'usn': s['usn'],
            'branch': s['branch'],
            'semester': s['semester']
        },
        'attendance': attendance_for(s['id']),
        'marks': [dict(x) for x in m],
        'materials': [dict(x) for x in mats]
    }

    system = (
        "You are SmartEdu AI, a helpful college assistant. "
        "Answer academic, programming, mathematics, science, engineering "
        "and general knowledge questions clearly. Use the supplied student "
        "context only for that student's personal data. Never reveal another "
        "student's information, passwords or OTPs. If information is missing, "
        "say so clearly."
    )

    messages = []
    for item in (history or [])[-12:]:
        if (isinstance(item, dict)
                and item.get('role') in ('user', 'assistant')
                and isinstance(item.get('content'), str)):
            messages.append({
                'role': item['role'],
                'content': item['content'][:6000]
            })

    messages.append({'role': 'user', 'content': q})
    system += """
Understand informal student messages, common chat abbreviations,
short forms, and minor spelling mistakes.
Examples:
- WT = what
- Y = why, when the context indicates why
- Ex = explain
- Diff = difference
- Def = define
- Hw = how
- imp = important
- n = and
- FCN = function, when the context is programming or technical.
Infer the intended question from context. If an abbreviation is
ambiguous, ask a short clarification instead of guessing.
Answer the intended question naturally and accurately.
"""
    full_system = (
        system + '\nAUTHORIZED STUDENT CONTEXT:\n'
        + json.dumps(context, ensure_ascii=False, default=str)
    )

    # Try local Ollama first.
    try:
        response = ollama.chat(
            model='llama3.2:1b',
            messages=[
                {'role': 'system', 'content': full_system},
                *messages
            ]
        )
        answer = response['message']['content'].strip()
        if answer:
            return answer
    except Exception as e:
        app.logger.warning("Ollama unavailable; trying OpenAI: %s", e)

    # Use OpenAI only if local Ollama fails.
    if not AI_API_KEY:
        raise RuntimeError(
            'Ollama is unavailable and OpenAI API key is not configured.'
        )

    payload = {
        'model': AI_MODEL,
        'instructions': full_system,
        'input': messages
    }

    req = urllib.request.Request(
        'https://api.openai.com/v1/responses',
        data=json.dumps(payload).encode(),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + AI_API_KEY
        }
    )

    with urllib.request.urlopen(req, timeout=45) as r:
        out = json.loads(r.read().decode())

    if out.get('output_text'):
        return out['output_text']

    parts = [
        content['text']
        for item in out.get('output', [])
        for content in item.get('content', [])
        if isinstance(content, dict) and content.get('text')
    ]

    if parts:
        return '\n'.join(parts)

    raise RuntimeError('No text returned by AI service')

def smart_local_answer(q,sid):
    ql=q.lower(); rows=attendance_for(sid); c=get_db(); marks=c.execute('SELECT * FROM marks WHERE student_id=? ORDER BY subject',(sid,)).fetchall(); mats=c.execute('SELECT * FROM materials WHERE college_id=(SELECT college_id FROM students WHERE id=?) ORDER BY id DESC',(sid,)).fetchall(); c.close()
    if any(x in ql for x in ['current attendance','overall attendance','my attendance','attendance percentage']):return f'Your current overall attendance is {overall_attendance(sid)}%.'
    if 'lowest attendance' in ql or 'low attendance' in ql:
        if rows:
            x=min(rows,key=lambda z:z['pct']);return f"Your lowest attendance is {x['subject']} at {x['pct']}% ({x['present']}/{x['total']})."
    for r in rows:
        if r['subject'].lower() in ql and 'attendance' in ql:return f"Your current {r['subject']} attendance is {r['pct']}% ({r['present']}/{r['total']} classes attended)."
    if 'attendance' in ql:return ' | '.join(f"{r['subject']}: {r['pct']}%" for r in rows) or 'No attendance records are available.'
    if any(x in ql for x in ['internal mark','internal marks','marks','ia marks']):
        for r in marks:
            if r['subject'].lower() in ql:
                total=sum(float(r[k]) for k in ['ia1','ia2','ia3','assignment']);return f"{r['subject']}: IA1 {r['ia1']}, IA2 {r['ia2']}, IA3 {r['ia3']}, Assignment {r['assignment']}. Total = {total:.0f}."
        return ' | '.join(f"{r['subject']}: {sum(float(r[k]) for k in ['ia1','ia2','ia3','assignment']):.0f}" for r in marks)
    if any(x in ql for x in ['notes','study material','materials','pdf','download','file','document']):return ('Available materials: '+', '.join(r['title'] for r in mats[:10])+'. Open Study Materials to view/download them.') if mats else 'No study materials uploaded yet.'
    if ql in {'hi','hello','hey'}:return 'Hello! I can answer academic and general questions, and I can check your own attendance and internal marks.'
    facts={'what is ai':'Artificial Intelligence (AI) is the field of building systems that can perform tasks that normally require human intelligence, such as learning, reasoning and language understanding.','what is machine learning':'Machine Learning is a branch of AI in which systems learn patterns from data to make predictions or decisions.','what is deep learning':'Deep Learning is a subset of machine learning that uses multi-layer neural networks to learn complex patterns from data.','what is python':'Python is a high-level, general-purpose programming language widely used in AI, data science and web development.','what is java':'Java is a general-purpose, object-oriented programming language widely used for enterprise, web and Android-related development.','what is dbms':'A DBMS is software used to create, store, organize, retrieve and manage data in databases.','what is sql':'SQL is a language used to create, query, update and manage data in relational databases.','what is computer network':'A computer network is a collection of connected devices that communicate and share resources.','what is operating system':'An operating system manages computer hardware and provides services and an interface for application software.','what is cloud computing':'Cloud computing provides computing resources such as storage, servers and software over a network, usually on demand.','what is nlp':'Natural Language Processing (NLP) is a field of AI that enables computers to process and understand human language.','what is big data':'Big Data refers to very large, fast and varied datasets that require scalable technologies for storage and analysis.','what is hadoop':'Hadoop is an open-source framework for distributed storage and processing of large datasets.','what is hive':'Hive is a data warehouse system on Hadoop that provides SQL-like querying and analysis of large datasets.','what is computer security':'Computer security protects systems, networks and data from unauthorized access, misuse and disruption.','what is cryptography':'Cryptography uses mathematical techniques to protect information through encryption, integrity and authentication.','what is database normalization':'Normalization organizes relational data to reduce redundancy and improve data integrity.','what is algorithm':'An algorithm is a finite sequence of well-defined steps used to solve a problem or perform a computation.','what is recursion':'Recursion is a programming technique in which a function solves a problem by calling itself on a smaller instance of the problem.','what is cnn':'A Convolutional Neural Network (CNN) is a deep-learning architecture commonly used for image and spatial-pattern processing.','what is reinforcement learning':'Reinforcement learning is a machine-learning approach where an agent learns actions through rewards and penalties.','what is excel':'Microsoft Excel is a spreadsheet application used for data entry, formulas, analysis, charts and reporting.'}
    for k,v in facts.items():
        if k in ql:return v
    return 'I can answer academic and general questions. Configure OPENAI_API_KEY for open-ended AI answers. I can always answer your personal attendance, marks and study-material questions from the authorized college database.'

@app.route('/admin-chatbot')
def admin_chatbot():
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    return render_template('admin_chatbot.html',faculty=f)

@app.route('/api/admin-chat',methods=['POST'])
def admin_chat():
    f=faculty()
    if not f:return jsonify({'answer':'Please log in first.'}),401
    q=str((request.json or {}).get('message','')).strip()
    if not q:return jsonify({'answer':'Please type a question.'})
    c=get_db(); count=c.execute('SELECT COUNT(*) FROM students WHERE college_id=?',(f['college_id'],)).fetchone()[0]; c.close()
    if AI_API_KEY:
        try:
            system='You are SmartEdu Admin AI. Answer naturally like a professional educational assistant. Use only the authorized college context supplied. Never reveal passwords, OTPs, or another college data.'
            payload={'model':AI_MODEL,'instructions':system+' Authorized college: '+f['college_name']+'; student count: '+str(count),'input':q}
            req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+AI_API_KEY})
            with urllib.request.urlopen(req,timeout=45) as r: out=json.loads(r.read().decode())
            if out.get('output_text'): return jsonify({'answer':out['output_text']})
        except Exception:
            app.logger.exception('SmartEdu admin AI provider request failed')
            return jsonify({'answer':'The AI service could not complete this request. Check OPENAI_API_KEY, SMARTEDU_AI_MODEL, internet access, and API usage/billing settings.','mode':'error'}), 502
    return jsonify({'answer':f"Your college currently has {count} students in SmartEdu. For open-ended ChatGPT-style answers, configure OPENAI_API_KEY in the project .env file.",'mode':'local','setup_required':True})

@app.get('/faculty/export/<kind>')
def faculty_export(kind):
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    from flask import send_file
    try:
        from openpyxl import Workbook
    except ImportError:
        return 'Excel export requires openpyxl. Restart SmartEdu after installing requirements.',500
    c=get_db()
    if kind=='attendance':
        rows=c.execute('SELECT s.name,s.usn,a.subject,a.class_date,a.status FROM attendance a JOIN students s ON s.id=a.student_id WHERE s.college_id=? ORDER BY a.subject,s.name,a.class_date',(f['college_id'],)).fetchall(); headers=['Student Name','USN','Subject','Date','Attendance']
    elif kind=='marks':
        rows=c.execute('SELECT s.name,s.usn,m.subject,m.ia1,m.ia2,m.ia3,m.assignment FROM marks m JOIN students s ON s.id=m.student_id WHERE s.college_id=? ORDER BY m.subject,s.name',(f['college_id'],)).fetchall(); headers=['Student Name','USN','Subject','IA-1','IA-2','IA-3','Assignment']
    elif kind=='students':
        rows=c.execute('SELECT name,usn,email,branch,semester FROM students WHERE college_id=? ORDER BY name',(f['college_id'],)).fetchall(); headers=['Student Name','USN','Email','Branch','Semester']
    else:c.close(); return 'Unknown export',400
    wb=Workbook(); ws=wb.active; ws.title=kind.title(); ws.append(headers)
    for r in rows: ws.append(list(r))
    for cell in ws[1]: cell.font=__import__('openpyxl').styles.Font(bold=True)
    c.close(); buf=io.BytesIO(); wb.save(buf); buf.seek(0)
    return send_file(buf,as_attachment=True,download_name=f'smartedu_{kind}.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ---------------- ADMIN ----------------


@app.route('/faculty/dashboard')
def faculty_dashboard():
    f = faculty()
    if not f:
        return redirect(url_for('faculty_login'))

    c = get_db()
    try:
        students = c.execute(
            '''SELECT * FROM students
               WHERE college_id = ?
               ORDER BY name''',
            (f['college_id'],)
        ).fetchall()

        mats = c.execute(
            '''SELECT * FROM materials
               WHERE college_id = ?
               ORDER BY id DESC LIMIT 8''',
            (f['college_id'],)
        ).fetchall()

        timetable_entries = c.execute(
            '''SELECT * FROM timetable
               WHERE college_id = ?
               ORDER BY day, start_time''',
            (f['college_id'],)
        ).fetchall()

        notifications = c.execute(
            '''SELECT * FROM notifications
               WHERE college_id = ?
               AND (audience IN ('all', 'students')
                    OR student_id IS NULL)
               ORDER BY id DESC LIMIT 8''',
            (f['college_id'],)
        ).fetchall()
    finally:
        c.close()

    return render_template(
        'faculty_dashboard.html',
        faculty=f,
        students=students,
        mats=mats,
        notifications=notifications,
        timetable_entries=timetable_entries
    )



def admin_owns_student(c,sid,fid):
    return c.execute('SELECT s.id FROM students s JOIN faculty f ON f.college_id=s.college_id WHERE s.id=? AND f.id=?',(sid,fid)).fetchone()

@app.post('/faculty/students/add')
def faculty_student_add():
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    name=request.form.get('name','').strip(); usn=request.form.get('usn','').strip().upper(); email=request.form.get('email','').strip().lower(); branch=request.form.get('branch','AI'); semester=int(request.form.get('semester','1') or 1); password=request.form.get('password','student123')
    if not name or not usn:return redirect(url_for('faculty_dashboard'))
    c=get_db()
    try:
        c.execute('INSERT INTO students(name,email,usn,branch,semester,password,college_id,mobile) VALUES(?,?,?,?,?,?,?,?)',(name,email,usn,branch,semester,generate_password_hash(password),f['college_id'],''));c.commit();flash('Student added.')
    except sqlite3.IntegrityError: flash('USN is already registered in this college.')
    c.close();return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/students/delete/<int:sid>')
def faculty_student_delete(sid):
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db()
    if not admin_owns_student(c,sid,f['id']):c.close();return 'Not authorized',403
    c.execute('DELETE FROM students WHERE id=?',(sid,));c.commit();c.close();flash('Student deleted.');return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/notify')
def faculty_notify():
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db(); c.execute('INSERT INTO notifications(title,message,audience,created_at,college_id) VALUES(?,?,?,?,?)',(request.form.get('title','College Notification'),request.form.get('message',''),'all',date.today().isoformat(),f['college_id'])); c.commit(); c.close(); flash('Notification published.'); return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/attendance/add')
def attendance_add():
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db(); sid=int(request.form['student_id'])
    if not admin_owns_student(c,sid,f['id']):c.close();return 'Not authorized',403
    try:c.execute('INSERT INTO attendance(student_id,subject,class_date,status) VALUES(?,?,?,?)',(sid,request.form['subject'],request.form['class_date'],request.form['status']));c.commit();flash('Attendance added.')
    except sqlite3.IntegrityError:flash('A record for this student, subject and date already exists.')
    c.close();return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/attendance/edit/<int:rid>')
def attendance_edit(rid):
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db(); row=c.execute('SELECT a.student_id FROM attendance a JOIN students s ON s.id=a.student_id WHERE a.id=? AND s.college_id=?',(rid,f['college_id'])).fetchone()
    if not row:c.close();return 'Not authorized',403
    c.execute('UPDATE attendance SET subject=?,class_date=?,status=? WHERE id=?',(request.form['subject'],request.form['class_date'],request.form['status'],rid));c.commit();c.close();flash('Attendance record updated.');return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/attendance/delete/<int:rid>')
def attendance_delete(rid):
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db();c.execute('DELETE FROM attendance WHERE id IN (SELECT a.id FROM attendance a JOIN students s ON s.id=a.student_id WHERE a.id=? AND s.college_id=?)',(rid,f['college_id']));c.commit();c.close();flash('Attendance record deleted.');return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/marks/save')
def marks_save():
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db();sid=int(request.form['student_id'])
    if not admin_owns_student(c,sid,f['id']):c.close();return 'Not authorized',403
    sub=request.form['subject'].strip();vals=[float(request.form.get(k,0) or 0) for k in ['ia1','ia2','ia3','assignment']];old=c.execute('SELECT id FROM marks WHERE student_id=? AND subject=?',(sid,sub)).fetchone()
    if old:c.execute('UPDATE marks SET ia1=?,ia2=?,ia3=?,assignment=? WHERE id=?',(*vals,old['id']));msg='Internal marks updated.'
    else:c.execute('INSERT INTO marks(student_id,subject,ia1,ia2,ia3,assignment) VALUES(?,?,?,?,?,?)',(sid,sub,*vals));msg='Internal marks added.'
    c.commit();c.close();flash(msg);return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/marks/delete/<int:rid>')
def marks_delete(rid):
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db();c.execute('DELETE FROM marks WHERE id IN (SELECT m.id FROM marks m JOIN students s ON s.id=m.student_id WHERE m.id=? AND s.college_id=?)',(rid,f['college_id']));c.commit();c.close();flash('Internal marks deleted.');return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/upload')
def upload():
    fadmin=faculty()
    if not fadmin:return redirect(url_for('faculty_login'))
    file=request.files.get('file')
    if not file or not file.filename:flash('Choose a file.');return redirect(url_for('faculty_dashboard'))
    ext=file.filename.rsplit('.',1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED:flash('Unsupported file type.');return redirect(url_for('faculty_dashboard'))
    filename=secure_filename(file.filename);stem,extension=os.path.splitext(filename);n=1
    while os.path.exists(os.path.join(UPLOADS,filename)):filename=f'{stem}_{n}{extension}';n+=1
    file.save(os.path.join(UPLOADS,filename));c=get_db();c.execute('INSERT INTO materials(title,subject,filename,file_type,uploaded_on,college_id) VALUES(?,?,?,?,?,?)',(request.form['title'],request.form['subject'],filename,ext,date.today().isoformat(),fadmin['college_id']));c.commit();c.close();flash('Material uploaded successfully.');return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/material/delete/<int:rid>')
def material_delete(rid):
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db();x=c.execute('SELECT filename FROM materials WHERE id=? AND college_id=?',(rid,f['college_id'])).fetchone()
    if x:
        try:os.remove(os.path.join(UPLOADS,x['filename']))
        except OSError:pass
        c.execute('DELETE FROM materials WHERE id=?',(rid,));c.commit()
    c.close();flash('Material deleted.');return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/notification')
def faculty_notification():
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db();student_id=request.form.get('student_id') or None
    if student_id and not admin_owns_student(c,int(student_id),f['id']):c.close();return 'Not authorized',403
    c.execute('INSERT INTO notifications(title,message,audience,student_id,created_at,college_id) VALUES(?,?,?,?,?,?)',(request.form['title'],request.form['message'],request.form.get('audience','all'),student_id,date.today().isoformat(),f['college_id']));c.commit();c.close();flash('Notification published to this college.');return redirect(url_for('faculty_dashboard'))

@app.post('/faculty/password')
def faculty_password():
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    old=request.form['old_password'];new=request.form['new_password']
    if len(new)<6:flash('New password must be at least 6 characters.');return redirect(url_for('faculty_dashboard'))
    c=get_db();row=c.execute('SELECT password FROM faculty WHERE id=?',(f['id'],)).fetchone()
    ok=row and password_ok(row['password'],old)
    if ok:c.execute('UPDATE faculty SET password=? WHERE id=?',(generate_password_hash(new),f['id']));c.commit();flash('Admin password changed.')
    else:flash('Old password is incorrect.')
    c.close();return redirect(url_for('faculty_dashboard'))

@app.route('/faculty/records')
def faculty_records():
    f=faculty()
    if not f:return redirect(url_for('faculty_login'))
    c=get_db();students=c.execute('SELECT * FROM students WHERE college_id=? ORDER BY name',(f['college_id'],)).fetchall();attendance_records={s['id']:c.execute('SELECT * FROM attendance WHERE student_id=? ORDER BY class_date DESC',(s['id'],)).fetchall() for s in students};marks_records={s['id']:c.execute('SELECT * FROM marks WHERE student_id=? ORDER BY subject',(s['id'],)).fetchall() for s in students};c.close();return render_template('faculty_records.html',students=students,attendance_records=attendance_records,marks_records=marks_records)

@app.context_processor
def inject_counts():
    return {'college_count':len(COLLEGES)+1}


@app.route('/faculty/timetable/add', methods=['POST'])
def add_timetable():
    f = faculty()
    if not f:
        return redirect(url_for('faculty_login'))

    branch = request.form.get('branch', '').strip()
    day = request.form.get('day', '').strip()
    start_time = request.form.get('start_time', '').strip()
    end_time = request.form.get('end_time', '').strip()
    subject = request.form.get('subject', '').strip()
    subject_code = request.form.get('subject_code', '').strip()
    faculty_name = request.form.get('faculty', '').strip()
    room = request.form.get('room', '').strip()

    try:
        semester = int(request.form.get('semester', ''))
        if not 1 <= semester <= 8:
            raise ValueError
    except ValueError:
        return 'Invalid semester', 400

    if not all([
        branch, day, start_time, end_time,
        subject, subject_code, faculty_name
    ]):
        return 'Please fill in all required fields', 400

    if day not in [
        'Monday', 'Tuesday', 'Wednesday',
        'Thursday', 'Friday', 'Saturday'
    ]:
        return 'Invalid day', 400

    if start_time >= end_time:
        return 'End time must be later than start time', 400

    c = get_db()
    try:
        c.execute(
            '''INSERT INTO timetable
               (college_id, branch, semester, day, start_time,
                end_time, subject, subject_code, faculty, room)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                f['college_id'], branch, semester, day,
                start_time, end_time, subject, subject_code,
                faculty_name, room
            )
        )
        c.commit()
    except Exception as e:
        c.rollback()
        app.logger.exception("Failed to add timetable entry")
        return f'Timetable save failed: {e}', 500
    finally:
        c.close()

    return redirect(url_for('faculty_dashboard') + '#timetable')


@app.route('/faculty/timetable/delete/<int:entry_id>',
           methods=['POST'])
def delete_timetable(entry_id):
    f = faculty()
    if not f:
        return redirect(url_for('faculty_login'))

    c = get_db()
    try:
        c.execute(
            'DELETE FROM timetable WHERE id = ? AND college_id = ?',
            (entry_id, f['college_id'])
        )
        c.commit()
    finally:
        c.close()

    return redirect(url_for('faculty_dashboard') + '#timetable')



@app.route('/faculty/timetable', methods=['GET', 'POST'])
def faculty_timetable_editor():
    f = faculty()
    if not f:
        return redirect(url_for('faculty_login'))

    days = ['Monday', 'Tuesday', 'Wednesday',
            'Thursday', 'Friday', 'Saturday']

    slots = [
        ('09:00', '10:00'),
        ('10:00', '11:00'),
        ('11:00', '11:10'),
        ('11:10', '12:10'),
        ('12:10', '13:00'),
        ('13:00', '14:00'),
        ('14:00', '15:00'),
        ('15:00', '16:00')
    ]

    labels = [
        '9–10 AM', '10–11 AM', 'BREAK (11–11:10 AM)',
        '11:10 AM–12:10 PM', 'LUNCH (12:10–1 PM)',
        '1–2 PM', '2–3 PM', '3–4 PM'
    ]

    branch = request.values.get('branch', '').strip()
    semester = request.values.get('semester', '1').strip()

    try:
        semester = int(semester)
        if not 1 <= semester <= 8:
            raise ValueError
    except (TypeError, ValueError):
        semester = 1

    c = get_db()

    if request.method == 'POST':
        try:
            if not branch:
                flash('Please enter a branch first.', 'error')
                c.close()
                return redirect(url_for('faculty_timetable_editor'))

            # Replace the existing timetable for this college,
            # branch and semester before saving the new one.
            c.execute(
                '''DELETE FROM timetable
                   WHERE college_id = ? AND branch = ? AND semester = ?''',
                (f['college_id'], branch, semester)
            )

            for day in days:
                for i, (start, end) in enumerate(slots):
                    subject = request.form.get(
                        f'subject_{day}_{i}', ''
                    ).strip()[:120]

                    lecturer = request.form.get(
                        f'faculty_{day}_{i}', ''
                    ).strip()[:120]

                    room = request.form.get(
                        f'room_{day}_{i}', ''
                    ).strip()[:50]

                    if i == 2:
                        subject = 'BREAK'
                    elif i == 4:
                        subject = 'LUNCH'

                    if subject:
                        c.execute(
                            '''INSERT INTO timetable
                               (college_id, branch, semester, day,
                                start_time, end_time, subject, faculty, room)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (f['college_id'], branch, semester, day,
                             start, end, subject, lecturer, room)
                        )

            c.commit()
            flash('Weekly timetable saved successfully!', 'success')

        except Exception:
            c.rollback()
            app.logger.exception('Could not save faculty timetable')
            flash('Could not save timetable. Please try again.', 'error')

        finally:
            c.close()

        return redirect(url_for(
            'faculty_timetable_editor',
            branch=branch,
            semester=semester
        ))
    
    rows = c.execute(
        '''SELECT * FROM timetable
           WHERE college_id = ? AND branch = ? AND semester = ?
           ORDER BY day, start_time''',
        (f['college_id'], branch, semester)
    ).fetchall()
    c.close()

    timetable = {
        (row['day'], row['start_time']): row
        for row in rows
    }

    return render_template(
        'faculty_timetable.html',
        faculty=f,
        days=days,
        slots=slots,
        labels=labels, 
        branch=branch,
        semester=semester,
        timetable=timetable
    )

if __name__ == '__main__':
    init_db()
    app.run(
        debug=False,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', '10000'))
   )
  