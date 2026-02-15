@echo off
echo Uygulama baslatiliyor, lutfen bekleyin...
echo PAWCO Magaza Takip
cd /d "%~dp0"
streamlit run app.py
pause