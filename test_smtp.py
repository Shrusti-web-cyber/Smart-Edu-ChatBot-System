
import os
import smtplib
import ssl
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(
    Path(__file__).resolve().parent / ".env",
    override=True
)

host = os.getenv("SMTP_HOST", "").strip()
port = int(os.getenv("SMTP_PORT", "587"))
user = os.getenv("SMTP_USER", "").strip()
password = "".join(os.getenv("SMTP_PASSWORD", "").split())

print("SMTP host:", host)
print("SMTP port:", port)
print("Username loaded:", bool(user))
print("App password length:", len(password))

stage = "connecting"

try:
    with smtplib.SMTP(host, port, timeout=20) as server:
        stage = "EHLO"
        server.ehlo()

        stage = "STARTTLS"
        server.starttls(context=ssl.create_default_context())
        print("TLS connection OK")

        stage = "EHLO after TLS"
        server.ehlo()

        print(
            "SMTP AUTH methods:",
            server.esmtp_features.get("auth", "NOT ADVERTISED")
        )

        stage = "Gmail login"
        server.login(user, password)
        print("SMTP LOGIN OK")

except Exception as e:
    print("FAILED AT:", stage)
    print("ERROR:", type(e).__name__, str(e))

    sender = os.getenv("SMTP_FROM", "").strip()

print("App password length:", len(password))
print("Sender matches username:", sender.lower() == user.lower())
