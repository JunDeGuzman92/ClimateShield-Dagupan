@echo off
REM Telegram field bot for ClimateShield - Dagupan (optional channel).
REM Needs a one-time @BotFather token in data\app_layers\bot_token.txt or the CS_TG_TOKEN env var.
REM Writes to this machine's crowd_reports.csv - run it beside the command center on the ops laptop.
cd /d "%~dp0"
python app\field_bot.py
pause