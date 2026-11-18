@echo off
title Aethelgard SIAT Terminator
echo ========================================================
echo        Aethelgard - SIAT Serverlarini To'xtatish
echo ========================================================
echo.

echo Port 8000 (Backend) va Port 5173 (Frontend) jarayonlari to'xtatilmoqda...
powershell -NoProfile -Command "8000, 5173 | ForEach-Object { $p = $_; Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 4 } | ForEach-Object { try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host ('Port ' + $p + ' (PID ' + $_.OwningProcess + ') to''xtatildi.') -ForegroundColor Green } catch {} } }"

echo.
echo ========================================================
echo   Barcha Aethelgard - SIAT serverlari to'xtatildi.
echo ========================================================
echo.
pause
