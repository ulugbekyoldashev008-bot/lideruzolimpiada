@echo off
cd /d %~dp0
if not exist venv (
  py -m venv venv
)
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env (
  copy .env.example .env
  echo .env fayli yaratildi. Uni to'ldirib, qayta ishga tushiring.
  pause
  exit /b
)
python main.py
pause
