@echo off
title VK BOT AUTO RESTART
:loop
echo Starting bot...
".venv\Scripts\python.exe" main.py
echo Bot crashed. Restarting in 3 seconds...
timeout /t 3
goto loop
