@echo off
chcp 65001 >nul
echo Запуск приложения...

if not exist .venv (
    echo Создание виртуального окружения...
    python -m venv .venv
)

echo Активация виртуального окружения
call .venv\Scripts\activate.bat

echo Установка зависимостей
pip3 install -r requirements.txt

echo Запуск приложения
python3 desktop.py

pause
