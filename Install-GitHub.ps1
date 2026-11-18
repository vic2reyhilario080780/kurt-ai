# Public source bootstrap. Provider keys are never downloaded from GitHub.
[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'Kurt'),
    [string]$CredentialsFile = ''
)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $InstallDir) {
    throw 'Install directory already exists. Choose a fresh -InstallDir; your existing installation was not overwritten.'
}
if ($CredentialsFile -and -not (Test-Path -LiteralPath $CredentialsFile -PathType Leaf)) {
    throw 'Encrypted credential file was not found. Copy your private .kurt-credentials file to this computer first.'
}
$KurtPython = $null
$KurtPythonArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -c 'import sys; raise SystemExit(sys.version_info < (3,10))'
    if ($LASTEXITCODE -eq 0) { $KurtPython = 'py'; $KurtPythonArgs = @('-3') }
}
if (-not $KurtPython -and (Get-Command python -ErrorAction SilentlyContinue)) {
    & python -c 'import sys; raise SystemExit(sys.version_info < (3,10))'
    if ($LASTEXITCODE -eq 0) { $KurtPython = 'python' }
}
if (-not $KurtPython) {
    throw 'Python 3.10+ is required. Install it from https://www.python.org/downloads/ (with its launcher), then rerun this command.'
}
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$KurtRepo = 'vic2reyhilario080780/kurt-ai'
$KurtHeaders = @{ 'User-Agent' = 'Kurt-Installer'; 'Accept' = 'application/vnd.github+json' }
$KurtRevision = (Invoke-RestMethod -Uri "https://api.github.com/repos/$KurtRepo/commits/main" -Headers $KurtHeaders).sha
if ($KurtRevision -notmatch '^[a-f0-9]{40}$') { throw 'GitHub returned an invalid source revision.' }
$KurtStage = Join-Path ([IO.Path]::GetTempPath()) ('kurt-install-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $KurtStage | Out-Null
try {
    $KurtArchive = Join-Path $KurtStage 'source.zip'
    Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/$KurtRepo/zip/$KurtRevision" -OutFile $KurtArchive
    Expand-Archive -LiteralPath $KurtArchive -DestinationPath $KurtStage
    $KurtSource = Join-Path $KurtStage "kurt-ai-$KurtRevision"
    if (-not (Test-Path -LiteralPath (Join-Path $KurtSource 'bootstrap.py') -PathType Leaf)) {
        throw 'Downloaded source did not contain the Kurt bootstrap.'
    }
    $KurtParent = Split-Path -Parent ([IO.Path]::GetFullPath($InstallDir))
    New-Item -ItemType Directory -Force -Path $KurtParent | Out-Null
    Move-Item -LiteralPath $KurtSource -Destination $InstallDir
    $KurtArguments = @((Join-Path $InstallDir 'bootstrap.py'))
    if ($CredentialsFile) { $KurtArguments += @('--credentials-file', ([IO.Path]::GetFullPath($CredentialsFile))) }
    & $KurtPython @KurtPythonArgs @KurtArguments
    if ($LASTEXITCODE -ne 0) { throw 'Kurt setup did not finish. Inspect the error above; source was retained for troubleshooting.' }
    Write-Host "Installed source revision: $KurtRevision"
    Write-Host ('Start Kurt: ' + (Join-Path $InstallDir 'Start Kurt.cmd'))
} finally {
    # Delete only this invocation's randomly named download staging directory.
    if (Test-Path -LiteralPath $KurtStage) { Remove-Item -LiteralPath $KurtStage -Recurse -Force }
}
