@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python bot.py
if %errorlevel% neq 0 (
    echo BOT CRASHED WITH ERROR CODE %errorlevel%
    pause
)
pause
