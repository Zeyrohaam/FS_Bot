@echo off
cd /d "%~dp0.."
start cmd /k python -m miniapp
ping 127.0.0.1 -n 3 > nul
start cmd /k python main.py
