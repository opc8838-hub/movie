@echo off
cd /d "%~dp0.."
python -X utf8 site\serve.py 8799
pause
