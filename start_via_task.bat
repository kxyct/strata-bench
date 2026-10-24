@echo off
title Strata LP engine
cd /d "D:\Strata\Strata-main"
"D:\Strata\Strata-main\.venv\Scripts\python.exe" "D:\Strata\Strata-main\serve\server.py" --engine strata --config "D:\Strata\Strata-main\strata-iq3_xxs.json" --port 8080
