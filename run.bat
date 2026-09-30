@echo off
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo .env faylini BOT_TOKEN va ADMIN_IDS bilan toldiring.
echo Keyin yana run.bat ni ishga tushiring.
python -m app.main
pause

