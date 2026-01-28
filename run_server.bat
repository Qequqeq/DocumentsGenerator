@echo off
echo ===============================
echo Starting server....
echo ===============================

if not exist .venv (
    echo now installing venv...
    python3 -m venv .venv
)

echo activation virtual enviroment
call .venv\Scripts\activate

echo installing requirements
pip3 install -r requirements.txt

echo server started
uvicorn api_entry:app 

pause
