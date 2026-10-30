@echo off
rem Launcher for Windows (cmd.exe and PowerShell): runs scripts\lab.py with Python 3.
rem Linux and macOS use the ./lab launcher. Run `lab --help` for the command overview.
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0scripts\lab.py" %*
  exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
  python "%~dp0scripts\lab.py" %*
  exit /b
)
echo lab: error: Python 3 was not found. Install it from https://www.python.org/downloads/ 1>&2
exit /b 3
