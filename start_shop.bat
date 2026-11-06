@echo off
chcp 65001 >nul
title MONO.DROP — Інтернет-магазин

cd /d "%~dp0"

echo =======================================================
echo          MONO.DROP — ЗАПУСК ЛОКАЛЬНОГО СЕРВЕРА
echo =======================================================
echo.

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

echo Запуск сервера та підключення публічного тунелю...
echo.
echo [ПІДКАЗКА] Щоб вимкнути сайт і закрити публічний тунель — просто закрийте це вікно або натисніть Ctrl+C.
echo.

python app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Помилка при виконанні сервера!
    pause
)
