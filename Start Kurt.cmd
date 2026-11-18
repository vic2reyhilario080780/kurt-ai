@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m kurt.main chat
) else (
  echo Run Install Kurt.cmd first.
)
pause
