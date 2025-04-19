@echo off
:: Check for admin rights
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [!] Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb runAs"
    exit /b
)

setlocal

:: Get folder where this script is located
set "SCRIPT_DIR=%~dp0"
set "DOWNLOAD_DIR=%SCRIPT_DIR%Downloads"
set "INSTALLER=OllamaSetup.exe"
set "INSTALLER_PATH=%DOWNLOAD_DIR%\%INSTALLER%"
set "OLLAMA_URL=https://ollama.com/download/OllamaSetup.exe"

:: Create the Downloads folder if it doesn't exist
if not exist "%DOWNLOAD_DIR%" (
    mkdir "%DOWNLOAD_DIR%"
)

echo [*] Downloading Ollama installer to: %INSTALLER_PATH%

:: Check if curl is available
where curl >nul 2>&1
if %errorLevel%==0 (
    echo [*] Using curl for fast download...
    curl -L -o "%INSTALLER_PATH%" "%OLLAMA_URL%"
) else (
    echo [*] curl not found, using PowerShell BITS transfer...
    powershell -Command "Start-BitsTransfer -Source '%OLLAMA_URL%' -Destination '%INSTALLER_PATH%'"
)

:: Check if download succeeded and run the installer
if exist "%INSTALLER_PATH%" (
    echo [*] Installer downloaded successfully.
    echo [*] Launching installer...
    start "" "%INSTALLER_PATH%"
) else (
    echo [!] Failed to download Ollama installer.
)

endlocal
pause
