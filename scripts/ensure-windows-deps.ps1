# Ensures .venv exists with chatxz deps (called automatically by run.ps1 / run.cmd).
param(
    [switch]$Quiet,
    [switch]$InstallPython
)

$script:RepoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { Get-Location }

function Test-Python310 {
    param([string]$Exe)
    if (-not $Exe) { return $false }
    & $Exe -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function Find-SystemPython {
    $localAppData = [Environment]::GetFolderPath('LocalApplicationData')
    $candidates = @(
        (Join-Path $localAppData 'Programs\Python\Python313\python.exe'),
        (Join-Path $localAppData 'Programs\Python\Python312\python.exe'),
        (Join-Path $localAppData 'Programs\Python\Python311\python.exe'),
        'C:\Program Files\Python313\python.exe',
        'C:\Program Files\Python312\python.exe',
        'C:\Program Files\Python311\python.exe'
    )
    foreach ($path in $candidates) {
        if ((Test-Path $path) -and (Test-Python310 $path)) { return $path }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return 'PYLAUNCHER' }
    }
    foreach ($name in @('python3', 'python')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notmatch 'WindowsApps' -and (Test-Python310 $cmd.Source)) {
            return $cmd.Source
        }
    }
    return $null
}

function Invoke-SystemPython {
    param([string[]]$PyArgs)
    if ($script:UsePyLauncher) {
        & py -3 @PyArgs
    } else {
        & $script:SystemPython @PyArgs
    }
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        throw "Python command failed (exit $LASTEXITCODE): $($PyArgs -join ' ')"
    }
}

function Ensure-SystemPython {
    $found = Find-SystemPython
    if ($found) {
        if ($found -eq 'PYLAUNCHER') {
            $script:UsePyLauncher = $true
            $script:SystemPython = $null
        } else {
            $script:UsePyLauncher = $false
            $script:SystemPython = $found
        }
        return
    }

    if ($InstallPython -and (Get-Command winget -ErrorAction SilentlyContinue)) {
        if (-not $Quiet) { Write-Host 'Installing Python 3.12 via winget...' }
        $null = winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements 2>&1
        $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
            [System.Environment]::GetEnvironmentVariable('Path', 'User')
        Ensure-SystemPython
        return
    }

    Write-Host 'Python 3.10+ not found.'
    Write-Host 'Install from https://www.python.org/downloads/windows/ (check Add to PATH),'
    Write-Host 'or re-run with winget available:  run.cmd web --share'
    exit 1
}

function Ensure-WindowsDeps {
    $venvPy = Join-Path $script:RepoRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPy) {
        return $venvPy
    }

    if (-not $Quiet) { Write-Host 'First run: setting up Python environment (.venv)...' }
    Ensure-SystemPython

    $venvDir = Join-Path $script:RepoRoot '.venv'
    Invoke-SystemPython @('-m', 'venv', $venvDir)

    $script:UsePyLauncher = $false
    $script:SystemPython = $venvPy

    if (-not $Quiet) { Write-Host 'Installing dependencies (rns, aiohttp)...' }
    Invoke-SystemPython @('-m', 'pip', 'install', '--upgrade', 'pip', '-q')
    Invoke-SystemPython @('-m', 'pip', 'install', 'rns>=1.3.0', 'aiohttp>=3.9.0', '-q')
    Invoke-SystemPython @('-m', 'pip', 'install', '-e', '.', '-q')

    return $venvPy
}