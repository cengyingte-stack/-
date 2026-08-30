@echo off
chcp 65001 >nul
title 微信实时字幕 - 首次安装
cd /d "%~dp0"

echo ============================================
echo   微信实时字幕 - 首次安装
echo ============================================
echo.
echo [1/4] 检查 Python...
where py >nul 2>nul
if %errorlevel% neq 0 (
    echo 未检测到 Python Launcher。
    echo 请先安装 Python 3.11 x64，并在安装时勾选 Add python.exe to PATH。
    echo 官方下载：https://www.python.org/downloads/windows/
    pause
    exit /b 1
)

echo [2/4] 创建虚拟环境...
if not exist ".venv\Scripts\python.exe" (
    py -3.10 -m venv .venv
    if %errorlevel% neq 0 (
        echo 创建环境失败。请确认已经安装 Python 3.11 x64。
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo [3/4] 升级 pip...
python -m pip install -U pip setuptools wheel
if %errorlevel% neq 0 goto :fail

echo [4/4] 安装依赖...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 goto :fail

echo.
echo ============================================
echo 安装完成。
echo 以后直接双击 start.bat 即可。
echo 第一次启动会下载 FunASR Paraformer 模型，需要联网。
echo ============================================
pause
exit /b 0

:fail
echo.
echo 安装失败。请复制上面的报错信息。
pause
exit /b 1
