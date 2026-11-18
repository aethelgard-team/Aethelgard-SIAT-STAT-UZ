@echo off
setlocal enabledelayedexpansion

title Aethelgard SIAT Launcher
echo ========================================================
echo        Aethelgard - SIAT Bir Klikda Ishga Tushirish
echo ========================================================
echo.

:: 1. Eski jarayonlarni tozalash (8000 va 5173 portlar)
echo [1/4] Eski portlar tekshirilmoqda va tozalanmoqda (8000, 5173)...
powershell -NoProfile -Command "8000, 5173 | ForEach-Object { $p = $_; Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 4 } | ForEach-Object { try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host ('Port ' + $p + ' tozalandi.') -ForegroundColor Yellow } catch {} } }"

:: 2. Python muhitini aniqlash
echo [2/4] Python muhiti tekshirilmoqda...
set "VENV_ACT="
if exist ".venv\Scripts\activate.bat" (
    set "VENV_ACT=call .venv\Scripts\activate.bat &&"
    echo .venv virtual muhiti topildi.
) else if exist "venv\Scripts\activate.bat" (
    set "VENV_ACT=call venv\Scripts\activate.bat &&"
    echo venv virtual muhiti topildi.
) else (
    echo Global Python ishlatiladi.
)

:: 3. FastAPI backend va Vite frontendni ishga tushirish
echo [3/4] FastAPI backend va Vite frontend ishga tushirilmoqda...
start "Aethelgard SIAT - FastAPI Backend (:8000)" cmd /k "%VENV_ACT% python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"
start "Aethelgard SIAT - Vite 3D Frontend (:5173)" cmd /k "cd frontend && npm run dev"

:: 4. Backend salomatligini kutish va brauzerni ochish
echo [4/4] Backend tayyorligi kutilmoqda (http://localhost:8000/health)...
powershell -NoProfile -Command "$sw = [System.Diagnostics.Stopwatch]::StartNew(); while ($sw.Elapsed.TotalSeconds -lt 30) { try { $res = Invoke-RestMethod -Uri 'http://localhost:8000/health' -TimeoutSec 2 -ErrorAction Stop; if ($res.status -eq 'ok') { Write-Host 'Backend muvaffaqiyatli ishga tushdi!' -ForegroundColor Green; break } } catch { Start-Sleep -Milliseconds 600 } }"

echo.
echo ========================================================
echo   Aethelgard - SIAT muvaffaqiyatli ishga tushirildi!
echo ========================================================
echo   - 3D Foydalanuvchi Interfeysi: http://localhost:5173
echo   - Taqdimot Demo Rejimi:        http://localhost:5173/?demo
echo   - Backend API Docs (Swagger):  http://localhost:8000/docs
echo   - Salomatlik Tekshiruvi:       http://localhost:8000/health
echo ========================================================
echo.

start http://localhost:5173

echo Serverlarni to'xtatish uchun istalgan vaqtda stop_siat.bat faylini ishga tushiring.
echo.
pause
