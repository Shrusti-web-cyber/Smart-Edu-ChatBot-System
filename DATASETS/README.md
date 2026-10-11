# SmartEdu datasets

- `colleges_catalog.csv`: public college catalog seeded into SmartEdu. `smartedu_code` is the app's internal display code (EE001, EE002, ...); it is a SmartEdu code, not an official VTU/AICTE code.
- `demo_students.csv`: synthetic demo students only. These are not real student records and must not be presented as real people.

For real deployment, import only student records supplied/authorized by the relevant college. Do not add passwords or OTPs to a CSV.

## Email OTP configuration
The app sends OTPs dynamically to the email address entered during signup. You do not create an OTP dataset. Configure the SMTP sender in `.env`:

SMARTEDU_SMTP_HOST=smtp.gmail.com
SMARTEDU_SMTP_PORT=587
SMARTEDU_SMTP_USER=your-sender@gmail.com
SMARTEDU_SMTP_PASSWORD=your-app-password
SMARTEDU_SMTP_FROM=your-sender@gmail.com

The previous OTP for the same email/role is deleted when a new OTP is issued. A used/expired OTP is not reusable.
