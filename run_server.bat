@echo off
echo ===============================
echo Запуск сервера
echo ===============================

REM Создаём venv если нет
if not exist .venv (
    echo Создаю виртуальное окружение...
    python -m venv .venv
)

echo Активирую виртуальное окружение...
call .venv\Scripts\activate

echo Устанавливаю зависимости...
pip install -r requirements.txt

echo Запускаю сервер...
uvicorn api_entry:app --host 127.0.0.1 --port 8000

pause
