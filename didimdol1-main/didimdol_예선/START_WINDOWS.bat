@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ==================================
echo  Didimdol Login + AI Training - v10
echo ==================================
python -m pip install -r requirements.txt
if errorlevel 1 ( echo Library installation failed & pause & exit /b 1 )
python -m streamlit run app.py
pause
