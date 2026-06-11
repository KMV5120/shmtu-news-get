@echo off
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
    choice /c YN /n /m "-> 选择: "
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

:: ── 检查/设置浏览器 ──────────────────────
call :setup_browser

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
    choice /c YN /n /m "-> 选择: "
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

:: ═══════════════════════════════════════════
:: 浏览器检测与设置
:: ═══════════════════════════════════════════
:setup_browser
set "EDGE_PATH="

:: 1. 快速检测 Playwright 自带 Chromium 是否已装（查文件，不启动浏览器）
set "PW_BROWSER_DIR=%USERPROFILE%\AppData\Local\ms-playwright"
set "PW_CHROMIUM_OK=0"
if exist "%PW_BROWSER_DIR%" (
    for /d %%d in ("%PW_BROWSER_DIR%\chromium-*") do (
        if exist "%%d\chrome-win\chrome.exe" set "PW_CHROMIUM_OK=1"
    )
)

if "%PW_CHROMIUM_OK%"=="1" (
    echo [√] Playwright Chromium 已安装
    goto :eof
)

:: 2. Playwright Chromium 未装，尝试用系统 Edge 替代
echo [!] Playwright Chromium 未安装
echo [>>] 尝试使用系统 Microsoft Edge 替代...

:: 2a. 标准路径 (x86)
if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    set "EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

:: 2b. 标准路径 (x64)
if "%EDGE_PATH%"=="" (
    if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
        set "EDGE_PATH=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    )
)

:: 2c. 桌面快捷方式
if "%EDGE_PATH%"=="" (
    for %%h in ("%USERPROFILE%\Desktop" "%PUBLIC%\Desktop") do (
        if exist "%%~h\Microsoft Edge.lnk" (
            set "EDGE_PATH=%%~h\Microsoft Edge.lnk"
        )
    )
)

:: 3. 找到了 Edge，设置环境变量
if not "%EDGE_PATH%"=="" (
    set "CHROMIUM_EXECUTABLE=%EDGE_PATH%"
    echo [√] 找到系统 Edge: "%EDGE_PATH%"
    echo [√] 已配置使用系统 Edge 作为浏览器引擎，无需下载额外文件
    goto :eof
)

:: 4. 没找到 Edge，提供选项
echo [X] 未找到 Microsoft Edge，需要安装浏览器引擎
echo.
echo ============================================
echo   浏览器引擎安装选项
echo ============================================
echo   1. 自动安装（从境外下载 ~182MB，可能很慢）
echo   2. 手动安装（复制下载链接到浏览器下载，通常更快）
echo   3. 跳过（本次不运行监控）
echo.
choice /c 123 /n /m "-> 选择 [1/2/3]: "
if !errorlevel! equ 3 goto :eof

if !errorlevel! equ 2 goto :manual_install

:: 自动安装
echo [>>] 正在自动安装 Playwright Chromium（可能较慢）...
python -m playwright install chromium
if !errorlevel! neq 0 (
    echo [X] 安装失败（网络问题常见），请尝试选项2手动安装
    pause
)
goto :eof

:manual_install
echo.
echo ============================================
echo   手动安装说明
echo ============================================
echo.
echo 1. 在浏览器中打开以下链接下载 Chromium：
echo    https://cdn.playwright.dev/builds/chromium/1140/chromium-win64.zip
echo.
echo 2. 下载完成后，解压到以下目录：
echo    %USERPROFILE%\AppData\Local\ms-playwright\chromium-1140\
echo.
echo    完整路径示例：
echo    %USERPROFILE%\AppData\Local\ms-playwright\chromium-1140\chrome-win\chrome.exe
echo.
echo 3. 重新运行本脚本即可。
echo.
echo 是否需要打开下载链接？[Y/N]
choice /c YN /n /m "-> 选择: "
if !errorlevel! equ 1 (
    start "" "https://cdn.playwright.dev/builds/chromium/1140/chromium-win64.zip"
)
echo.
echo 按任意键继续...
pause >nul
goto :eof

:end
echo 感谢使用！
endlocal
exit /b 0
