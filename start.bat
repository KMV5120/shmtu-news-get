@echo off
:: Launcher: set UTF-8 codepage before parsing the main script
chcp 65001 >nul 2>&1
call "%~dp0run.bat"
