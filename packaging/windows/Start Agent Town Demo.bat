@echo off
setlocal
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start Agent Town Demo.ps1"
if errorlevel 1 (
    echo.
    echo Agent Town Demo failed to start. See the message above.
    pause
)
endlocal
