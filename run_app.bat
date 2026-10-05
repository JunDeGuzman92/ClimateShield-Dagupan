@echo off
REM ClimateShield - Dagupan Command Center launcher
cd /d "%~dp0"
echo Starting ClimateShield Dagupan Command Center...
echo Opening http://localhost:8501 in your browser (Ctrl+C here to stop the server)
start "" http://localhost:8501
python -m streamlit run app\climateshield_command_center.py --server.headless true --server.port 8501
