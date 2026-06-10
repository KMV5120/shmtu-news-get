@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ──────────────────────────────────────────────
::  上海海事大学数字平台监控 — 启动脚本
:: ──────────────────────────────────────────────

title 数字平台监控

cd /d "%~dp0"

:: ── 检查 Python ──────────────────────────────
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] 未检测到 Python，请先安装 Python 3.10+
    echo     下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [√] Python %PYVER%

:: ── 检查依赖 ──────────────────────────────
python -c "import requests, bs4, lxml, PIL, playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] 依赖未安装，是否立即安装？[Y/N]
    choice /c YN /n /m "→ 选择: "
    if !errorlevel! equ 2 exit /b 1
    echo [>>] 正在安装依赖...
    pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [X] 依赖安装失败，请检查网络或手动安装
        pause
        exit /b 1
    )
    echo [√] 依赖安装完成
)

:: ── 检查 Playwright 浏览器 ─────────────────
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); b.close(); p.stop()" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] Playwright 浏览器未安装，正在安装 Chromium...
    python -m playwright install chromium
    if !errorlevel! neq 0 (
        echo [X] Playwright 浏览器安装失败
        pause
        exit /b 1
    )
    echo [√] Chromium 安装完成
)

:: ── 检查配置 ──────────────────────────────
python -c "import json; c=json.load(open('config.json','r',encoding='utf-8')); assert c.get('username','').strip() not in ('','你的学号或工号'); assert c.get('password','').strip() not in ('','你的统一认证密码'); assert c.get('pushplus_token','').strip() not in ('','你的PushPlusToken')" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [X] config.json 未正确配置
    echo     请编辑 config.json 填入以下信息:
    echo       - username:   学号或工号
    echo       - password:   统一认证密码
    echo       - pushplus_token: PushPlus Token
    echo       - deepseek_api_key: DeepSeek API Key
    echo.
    echo     是否用记事本打开 config.json 编辑？[Y/N]
    choice /c YN /n /m "→ 选择: "
    if !errorlevel! equ 1 notepad config.json
    exit /b 1
)

:: ── 主菜单 ─────────────────────────────────
:menu
cls
echo.
echo ╔══════════════════════════════════════════════╗
echo ║     上海海事大学数字平台监控系统              ║
echo ╠══════════════════════════════════════════════╣
echo ║  1.  运行监控（抓取 + AI 摘要 + 微信推送）    ║
echo ║  2.  测试微信推送                            ║
echo ║  3.  安装 Windows 定时任务（每周六 18:00）   ║
echo ║  4.  探索页面结构（调试用）                  ║
echo ║  5.  退出                                    ║
echo ╚══════════════════════════════════════════════╝
echo.
set "choice="
set /p choice="请输入选项 [1-5]: "
if "%choice%"=="1" goto run_monitor
if "%choice%"=="2" goto run_test
if "%choice%"=="3" goto run_setup
if "%choice%"=="4" goto run_discover
if "%choice%"=="5" goto end
echo 无效选项，请重新输入
pause
goto menu

:: ── 运行监控 ──────────────────────────────
:run_monitor
echo.
echo [>>] 正在启动监控...
echo.
python main.py
echo.
echo 按任意键返回菜单...
pause >nul
goto menu

:: ── 测试推送 ──────────────────────────────
:run_test
echo.
echo [>>] 发送测试消息到微信...
echo.
python main.py --test
echo.
echo 按任意键返回菜单...
pause >nul
goto menu

:: ── 安装定时任务 ──────────────────────────
:run_setup
echo.
echo [>>] 创建每周六 18:00 自动监控任务...
echo.
python main.py --setup
echo.
echo 按任意键返回菜单...
pause >nul
goto menu

:: ── 探索页面 ──────────────────────────────
:run_discover
echo.
echo [>>] 探索模式 — 分析页面结构...
echo.
python main.py --discover
echo.
echo 按任意键返回菜单...
pause >nul
goto menu

:end
echo 感谢使用！
endlocal
exit /b 0
