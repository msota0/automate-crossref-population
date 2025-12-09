@echo off

REM Check if Python was installed successfully
echo Verifying Python installation...
python --version

REM Pause to keep the window open to view results
pip install -r requirements.txt
pause


