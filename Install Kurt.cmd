@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 bootstrap.py %*
) else (
  python bootstrap.py %*
)
set "kurt_result=%errorlevel%"
if not "%kurt_result%"=="0" echo Setup incomplete. Python 3.10+ is required: https://www.python.org/downloads/
pause
exit /b %kurt_result%
