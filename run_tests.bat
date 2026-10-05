@echo off
REM Run the full ClimateShield test suite (about 10-15 minutes; app pages are booted headlessly).
REM Your own data (prefs, requests, shelters, exercise history) is backed up and restored by the tests.
cd /d "%~dp0"
python -m pytest %*
pause
