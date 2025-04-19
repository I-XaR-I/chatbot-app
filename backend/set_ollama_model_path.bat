@echo off
:: Elevate to admin if not already
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb runAs"
    exit /b
)

echo [*] Setting up custom model folder for Ollama...

:: Define default and target paths
set "DEFAULT_MODEL_DIR=%USERPROFILE%\.ollama\models"
set "CUSTOM_MODEL_DIR=%~dp0..\models"

:: Normalize the custom path
for %%I in ("%CUSTOM_MODEL_DIR%") do set "CUSTOM_MODEL_DIR=%%~fI"

:: Create the custom folder if it doesn't exist
if not exist "%CUSTOM_MODEL_DIR%" (
    echo [*] Creating custom model directory at: %CUSTOM_MODEL_DIR%
    mkdir "%CUSTOM_MODEL_DIR%"
)

:: If the default model dir exists and is not a symlink, move its contents
if exist "%DEFAULT_MODEL_DIR%" (
    dir /a:l "%DEFAULT_MODEL_DIR%" >nul 2>&1
    if errorlevel 1 (
        echo [*] Moving existing models to new location...
        xcopy "%DEFAULT_MODEL_DIR%\*" "%CUSTOM_MODEL_DIR%\" /E /H /Y
        rmdir /S /Q "%DEFAULT_MODEL_DIR%"
    ) else (
        echo [*] Existing symbolic link found. Replacing...
        rmdir "%DEFAULT_MODEL_DIR%"
    )
)

:: Create symlink
mklink /D "%DEFAULT_MODEL_DIR%" "%CUSTOM_MODEL_DIR%"

echo [✓] Done! Ollama will now use: %CUSTOM_MODEL_DIR%
pause
