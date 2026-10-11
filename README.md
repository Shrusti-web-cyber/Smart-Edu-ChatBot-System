# SmartEdu – Final Multi-College + Signup + AI Edition

SmartEdu is a Flask-based multi-college student academic assistant.

## Role flow

1. Home page shows only two choices: **Sign in as Student** and **Sign in as Admin**. No chatbot artwork, signup button, or extra descriptive text is shown there.
2. Student Login opens only the student authentication flow.
3. Admin Login opens only the admin authentication flow.
4. The Student Dashboard never exposes an Admin Login button.
5. The Admin Dashboard never exposes a Student Login button.
6. Backend sessions store the authenticated `student_id` or `faculty_id`; college and student authorization is enforced server-side.

## Student signup

Signup is kept as a setup flow, but no signup button/link is displayed on the public login screen.

- Full name
- College
- Email
- Email OTP verification
- Mobile number
- USN
- Branch
- Semester
- Password + confirmation

## Admin signup

Signup is kept as a setup flow, but no signup button/link is displayed on the public login screen.

- Admin name
- College
- Admin email
- Email OTP verification
- Mobile number
- Password + confirmation

## Email OTP setup

The project sends OTPs through SMTP. It does not magically send email without an email provider account.

Copy `.env.example` to `.env` (or set the same environment variables in Windows) and configure:

- `SMARTEDU_SMTP_HOST`
- `SMARTEDU_SMTP_PORT`
- `SMARTEDU_SMTP_USER`
- `SMARTEDU_SMTP_PASSWORD`
- `SMARTEDU_SMTP_FROM`

For Gmail, use an App Password with an account that has 2-Step Verification enabled; do not put your normal email password into the project.

### Email OTP flow

Signup → enter email → server generates a random 6-digit OTP → OTP hash is stored in the database → OTP is emailed through SMTP → user enters OTP → server checks the hash and 10-minute expiry → account is created.

### Mobile OTP

The requested signup flow uses **email OTP**. If SMS OTP is required later, add a compliant SMS provider integration and keep the same server-side verification pattern. Do not put provider secrets in frontend JavaScript.

## AI chatbot

Set `OPENAI_API_KEY` in the project-root `.env` file and use `SMARTEDU_AI_MODEL=gpt-4.1-mini` (or another model enabled for your API account). The project loads `.env` at startup. The app sends the authenticated student's authorized academic context only; it does not intentionally send other students' records to the student chatbot. The chatbot is open-ended ChatGPT-style AI only when a valid API key, model access, internet connection and API usage/billing are available. Without a key, only limited local fallback answers work. See `SETUP_AI_AND_RUN.txt`.

A ChatGPT subscription and API usage are separate services/billing systems; a ChatGPT login cannot simply be embedded as the project's API credential.

## Run on Windows / Microsoft Edge

Double-click `run_smartedu.bat`, or run:

```text
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Then open:

`http://127.0.0.1:5000`

The included batch file attempts to open Microsoft Edge automatically.

## Demo account

Student:
- College: Demo College
- Name: Shrusti
- USN: `1BK22AI001`
- Password: `student123`

Admin:
- College: Demo College
- Name: `Admin-EE156` (SmartEdu demo admin name may vary with seeded college code)
- Password: `admin123`

## Important data note

The college catalog is based on public institution information and the student/attendance/marks records included for testing are synthetic demo records. Do not present them as real student data. For real deployment, each college should import its authorized student roster and academic records.

## Updated email verification UI
- There is no Confirm Email ID field.
- Signup has Email ID + Verify Email ID (OTP) in the same row.
- Send OTP sends a fresh 6-digit OTP to the entered address.
- Any previous OTP for that email and role is deleted before a new OTP is created.
- After successful verification, the OTP record is deleted from the database.
- A green `✓ Email verified` status is shown after correct OTP.
- Invalid email syntax or wrong/expired OTP shows a red `✖` status.
- An email address is considered verified only after the server confirms the OTP.

## Configure email delivery
Create a `.env` file beside `app.py` and set the SMTP values from your email provider. For Gmail, enable 2-Step Verification and create a Google App Password; use that 16-character App Password as `SMARTEDU_SMTP_PASSWORD`, not your normal Gmail password.

Example:
SMARTEDU_SMTP_HOST=smtp.gmail.com
SMARTEDU_SMTP_PORT=587
SMARTEDU_SMTP_USER=yourgmail@gmail.com
SMARTEDU_SMTP_PASSWORD=your-16-character-app-password
SMARTEDU_SMTP_FROM=yourgmail@gmail.com

The app does not need a database list of every user's email password. Each user supplies their own email during signup, and the SMTP service sends the one-time code to that address. The app stores only a hash of the OTP and expires it after 10 minutes.

## Latest SmartEdu build changes

- Student signup uses one Email ID field plus OTP verification; there is no confirmation-email field.
- Invalid email format is rejected in the browser and server.
- A new OTP deletes the previous OTP for the same email/role; verified/expired OTPs cannot be reused.
- Student and admin sessions are strictly separated. Student pages do not show Admin Login; admin pages do not show Student Login.
- Added SmartEdu-facing college codes such as `EE001`, `EE002`, etc. These are internal app identifiers, not official university codes.
- Added synthetic college/student datasets under `DATASETS/`.
- Added editable personal study planner and AI quiz entry point.
- Materials downloads remain college-scoped.
- Real student records, emails, passwords, marks and attendance must be imported only with authorization from the relevant college.

## Email OTP: what data is needed

Do not create a spreadsheet of OTPs. OTPs are generated dynamically per verification request. Configure one SMTP sender account in `.env`; the recipient email is supplied by the student/admin during signup.

Required SMTP settings:

`SMARTEDU_SMTP_HOST`
`SMARTEDU_SMTP_PORT`
`SMARTEDU_SMTP_USER`
`SMARTEDU_SMTP_PASSWORD`
`SMARTEDU_SMTP_FROM`

For Gmail, use a Google App Password for the SMTP password. Never store a student's personal email password in SmartEdu.

## College catalog scope

The included catalog is a public VTU-focused seed for development/testing. VTU's public consortium describes 200+ affiliated engineering colleges, and the VTU site maintains affiliated/autonomous/regional lists. For a production deployment that claims complete Karnataka coverage, refresh the catalog from authoritative current institutional sources before importing it.


## Student UI refresh
- Landing page contains only Student Login and Admin Login.
- Student Login contains only Student Name, Student Email and Password.
- Admin Login contains only Admin Name and Password.
- Login screens do not show signup links or cross-role login options.
- Student dashboard uses a dark professional layout with a left feature sidebar: Dashboard, Attendance, Internal Marks, AI Chatbot, Download, Personalized Study Plan, AI Quiz, Notifications and College Information.
- Dashboard main area shows college, student name, college, USN and overall attendance, plus a subject-wise attendance bar chart. Internal marks are not displayed on the main dashboard.
- A professional SmartEdu chatbot illustration is included in `static/chatbot-professional.svg`.


## Final AI setup and app launch

See `SETUP_AI_AND_RUN.txt` for the step-by-step Windows/Edge setup. The visual style uses navy and deep green backgrounds, purple accents, grey buttons, white content cards, and color-coded tables.
