# Build chatxz Windows portable zip (run on Windows with Python 3.11+).
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

$Version = (Select-String -Path "chatxz\_version.py" -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value
Write-Host "Building chatxz v$Version portable for Windows..."

python -m pip install --upgrade pip
python -m pip install "rns>=1.3.0" "aiohttp>=3.9.0" pyinstaller
python -m pip install -e .

if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }

pyinstaller --noconfirm packaging/windows/chatxz-portable.spec

$DistDir = Join-Path $Root "dist\chatxz"
if (-not (Test-Path (Join-Path $DistDir "chatxz.exe"))) {
    throw "Build failed: dist\chatxz\chatxz.exe not found"
}

Copy-Item (Join-Path $Root "packaging\windows\README-PORTABLE.txt") $DistDir -Force

$ZipName = "chatxz-$Version-windows-portable.zip"
$ZipPath = Join-Path $Root "dist\$ZipName"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $DistDir -DestinationPath $ZipPath -Force

Write-Host "Done: $ZipPath"
Write-Host "Unzip, then double-click chatxz.exe inside the folder."