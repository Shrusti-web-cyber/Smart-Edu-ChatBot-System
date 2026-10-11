@echo off
cd /d "%~dp0"
echo Starting SmartEdu...
if not exist .venv (
  echo Creating Python virtual environment...
  py -m venv .venv
)
call .venv\Scripts\activate
python -m pip install -r requirements.txt
start "SmartEdu - Microsoft Edge" msedge http://127.0.0.1:5000
python app.py
pause
