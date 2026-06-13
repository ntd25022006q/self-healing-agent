# Self-Healing Agent installer script for Windows PowerShell
# Mimics Aider's PowerShell installer to create virtual environments and PATH commands

$ErrorActionPreference = "Stop"

Write-Host "=== Self-Healing Agent Windows Installer ===" -ForegroundColor Green

# 1. Check Python installation
try {
    $pythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    Write-Host "[Info] Found Python version: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Error "[Error] Python is not installed or not in PATH. Please install Python 3.9+."
    Exit 1
}

# 2. Setup isolated env
$installDir = Join-Path $env:USERPROFILE ".self-healing-agent"
if (!(Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir | Out-Null
}

# Clone or download ZIP
$gitPath = Get-Command git -ErrorAction SilentlyContinue
if ($gitPath) {
    if (Test-Path (Join-Path $installDir ".git")) {
        Write-Host "[Info] Updating existing repository..." -ForegroundColor Cyan
        Set-Location $installDir
        & git pull
    } else {
        Write-Host "[Info] Cloning repository..." -ForegroundColor Cyan
        & git clone https://github.com/ntd25022006q/self-healing-agent.git $installDir
    }
} else {
    Write-Host "[Warning] Git not found. Downloading ZIP archive..." -ForegroundColor Yellow
    $zipUrl = "https://github.com/ntd25022006q/self-healing-agent/archive/refs/heads/main.zip"
    $zipPath = Join-Path $installDir "archive.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
    
    # Extract ZIP
    Expand-Archive -Path $zipPath -DestinationPath $installDir -Force
    $extractedDir = Join-Path $installDir "self-healing-agent-main"
    Move-Item -Path "$extractedDir\*" -Destination $installDir -Force
    Remove-Item -Path $extractedDir -Recurse -Force
    Remove-Item -Path $zipPath -Force
}

# 3. Create virtual environment
Write-Host "[Info] Creating virtual environment..." -ForegroundColor Cyan
& python -m venv "$installDir\venv"
$pipPath = Join-Path $installDir "venv\Scripts\pip.exe"
$pythonExec = Join-Path $installDir "venv\Scripts\python.exe"

& $pipPath install --upgrade pip
& $pipPath install -r "$installDir\requirements.txt"
& $pipPath install -e $installDir

# 4. Create launch batch scripts in a folder and add to Path
$binDir = Join-Path $env:USERPROFILE "AppData\Local\Microsoft\WindowsApps" # Default user path folder
if (!(Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir | Out-Null
}

# Create heal.bat
$healBatContent = @"
@echo off
"$pythonExec" "$installDir\main.py" %*
"@
$healBatContent | Out-File -FilePath (Join-Path $binDir "heal.bat") -Encoding ascii

# Create shc.bat
$shcBatContent = @"
@echo off
"$pythonExec" "$installDir\main.py" %*
"@
$shcBatContent | Out-File -FilePath (Join-Path $binDir "shc.bat") -Encoding ascii

Write-Host "==================================================" -ForegroundColor Green
Write-Host "SUCCESS! Self-Healing Agent installed successfully." -ForegroundColor Green
Write-Host "CLI scripts created in: $binDir" -ForegroundColor Cyan
Write-Host "You can now run:" -ForegroundColor Cyan
Write-Host "  heal --help" -ForegroundColor Yellow
Write-Host "  shc --help" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Green
