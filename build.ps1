# Build the Bible object model on Windows, natively (no WSL).
#
# From this folder, in PowerShell:
#     powershell -ExecutionPolicy Bypass -File .\build.ps1
#
# It makes a private Python environment in .venv, installs what requirements.txt lists, fetches the pinned
# sources, builds everything into dist\, then runs the tests. Safe to run again: it reuses what is already there.
# Add -SkipTests to skip the tests.
param([switch]$SkipTests)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'   # Greek and Hebrew print safely on any console code page

function Run([string]$exe, [string[]]$argv) {
    & $exe @argv
    if ($LASTEXITCODE -ne 0) { throw "This step failed (exit code $LASTEXITCODE): $exe $($argv -join ' ')" }
}

# 1. Check for Git and Python 3.10 or newer.
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git was not found. Install Git for Windows (https://git-scm.com/download/win), open a new PowerShell window, and run this again.'
}
[string[]]$base = if (Get-Command py -ErrorAction SilentlyContinue) { @('py', '-3') }
        elseif (Get-Command python -ErrorAction SilentlyContinue) { ,@('python') }
        else { throw 'Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/ (tick "Add python.exe to PATH"), open a new PowerShell window, and run this again.' }
$pyExe = $base[0]; $pyArgs = @($base | Select-Object -Skip 1)
& $pyExe @pyArgs -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'This needs Python 3.10 or newer. Install it from https://www.python.org/downloads/ and run this again.' }

# 2. A private Python environment, so nothing is installed into your main Python.
$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPy)) {
    Write-Host '== Making the Python environment (.venv)'
    Run $pyExe ($pyArgs + @('-m', 'venv', '.venv'))
}
Write-Host '== Installing requirements'
Run $venvPy @('-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r', 'requirements.txt')

# 3. Fetch the pinned sources and build everything (data files, maps, vault, graph viewer).
Write-Host '== Building (the first run downloads the sources and takes a few minutes)'
Run $venvPy @('build\make_all.py')

# 4. Tests: the ten gates plus the layer tests.
if (-not $SkipTests) {
    Write-Host '== Running the tests'
    Run $venvPy @('-m', 'pytest', '-q', 'tests')
}

# 5. What you got, and how to hook it to Claude.
$hash = (& $venvPy 'build\data_hash.py' | Out-String).Trim()
$config = @{ mcpServers = @{ 'bible-object-model' = @{
    command = $venvPy
    args    = @((Join-Path $PSScriptRoot 'mcp_server\server.py'))
} } } | ConvertTo-Json -Depth 5
Write-Host ''
Write-Host 'Done.'
Write-Host "  Data file:  $(Join-Path $PSScriptRoot 'dist\acts-core.sqlite')"
Write-Host "  Data hash:  $hash"
Write-Host "  Graph:      $(Join-Path $PSScriptRoot 'dist\graph\index.html')"
Write-Host "  Vault:      $(Join-Path $PSScriptRoot 'dist\vault')"
Write-Host ''
Write-Host 'To use it from Claude Desktop, add this to its config (Settings, Developer, Edit Config):'
Write-Host $config
