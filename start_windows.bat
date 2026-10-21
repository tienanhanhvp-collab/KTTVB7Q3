@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
 echo Cai Python 3 va thu lai.
 pause
 exit /b 1
)
echo Giao vien: http://localhost:8000/teacher
py -3 -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
