@echo off
title R1 AutoPatch Script Manager
cd /d "%~dp0"
python push_autopatch.py
if errorlevel 1 pause
