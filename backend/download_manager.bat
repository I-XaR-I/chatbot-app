@echo off
echo Starting Ollama Model Manager...
python ollama_manager.py
if %ERRORLEVEL% NEQ 0 (
    echo Error running Ollama Model Manager. Error code: %ERRORLEVEL%
    echo Please check if Python is installed and the script exists.
    pause
    exit /b %ERRORLEVEL%
)
pause
