# Isolated Windows setup; no execution-policy or global package changes.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 bootstrap.py @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python bootstrap.py @args
} else {
    Write-Error "Install Python 3.10+ from https://www.python.org/downloads/ and enable its launcher."
    exit 1
}
exit $LASTEXITCODE
