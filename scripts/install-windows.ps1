# Optional extras (voice). Normal use: run.cmd web --share  (no separate install).
param(
    [switch]$Voice,
    [switch]$InstallPython,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

. (Join-Path $RepoRoot 'scripts\ensure-windows-deps.ps1')

Write-Host 'chatxz - Windows optional setup'
Write-Host '================================'
Write-Host ''
Write-Host 'Tip: you usually only need:  run.cmd web --share'
Write-Host ''

$null = Ensure-WindowsDeps -InstallPython:$InstallPython

$venvPy = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$script:UsePyLauncher = $false
$script:SystemPython = $venvPy

if ($Voice) {
    Write-Host 'Installing voice support (pyaudio)...'
    & $venvPy -m pip install pyaudio
} elseif (-not $NonInteractive) {
    $voiceOpt = Read-Host 'Install voice support (pyaudio)? [y/N]'
    if ($voiceOpt -match '^[Yy]') {
        & $venvPy -m pip install pyaudio
    }
}

Write-Host ''
Write-Host 'Ready. Start server:  run.cmd web --share'