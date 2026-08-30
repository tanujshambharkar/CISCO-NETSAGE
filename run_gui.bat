@echo off
setlocal
echo Starting NetSage AI Desktop GUI...
cd /d "%~dp0"

REM Prefer virtual environment python if it exists
if exist "%~dp0..\.venv_gui\bin\python.exe" (
    "%~dp0..\.venv_gui\bin\python.exe" "%~dp0src\gui.py"
    goto end
)

if exist "%~dp0.venv_gui\bin\python.exe" (
    "%~dp0.venv_gui\bin\python.exe" "%~dp0src\gui.py"
    goto end
)

if exist "C:\msys64\mingw64\bin\python.exe" (
    "C:\msys64\mingw64\bin\python.exe" "%~dp0src\gui.py"
    goto end
)

python "%~dp0src\gui.py"

:end
endlocal
