@echo off
setlocal
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
start "" pythonw -m stmlab.gui
