@echo off
chcp 65001 >nul
title 微信实时字幕
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 尚未安装，请先双击 install.bat
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python app.py
if %errorlevel% neq 0 (
    echo.
    echo 程序异常退出，请把上面的报错内容复制出来。
    pause
)
