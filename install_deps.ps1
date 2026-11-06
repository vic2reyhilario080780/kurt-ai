# ============================================================
# KURT v3.0 — One-command setup (Windows PowerShell)
# Run once after cloning:  .\install_deps.ps1
#
# LAHAT ng tools nasa project folder — walang global installs!
# macOS/Linux users: use install_deps.sh instead
# ============================================================

$ErrorActionPreference = "Stop"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

Write-Host ""
Write-Host "🤖 Setting up K.U.R.T. — Kinetic Unified Response Terminal" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "   Platform: Windows"
Write-Host ""

# ── Node / npm tools ─────────────────────────────────────────
Write-Host "📦 Installing npm tools (Claude Code CLI, Gemini CLI)..." -ForegroundColor Yellow
if (Get-Command node -ErrorAction SilentlyContinue) {
    npm install --prefix $SCRIPT_DIR
    Write-Host "   ✓ node_modules/ created — lahat naka-local sa project" -ForegroundColor Green
} else {
    Write-Host "   ⚠  Node.js not found. Install from: https://nodejs.org" -ForegroundColor Red
    Write-Host "   ⚠  Skipping Claude Code CLI + Gemini CLI" -ForegroundColor Red
}
Write-Host ""

# ── Python deps ──────────────────────────────────────────────
Write-Host "🐍 Installing Python dependencies..." -ForegroundColor Yellow
if (Get-Command pip -ErrorAction SilentlyContinue) {
    pip install -r requirements.txt -q
    Write-Host "   ✓ requirements.txt installed" -ForegroundColor Green
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m pip install -r requirements.txt -q
    Write-Host "   ✓ requirements.txt installed (via python -m pip)" -ForegroundColor Green
} else {
    Write-Host "   ❌ Python not found. Install from: https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host ""

# ── Playwright browser ───────────────────────────────────────
Write-Host "🌐 Installing Playwright browser (for web automation)..." -ForegroundColor Yellow
try {
    python -m playwright install chromium 2>$null
    Write-Host "   ✓ Chromium installed" -ForegroundColor Green
} catch {
    Write-Host "   ⚠  Playwright chromium skipped (run: playwright install chromium)" -ForegroundColor Yellow
}
Write-Host ""

# ── KURT itself ──────────────────────────────────────────────
Write-Host "⚙️  Installing KURT CLI..." -ForegroundColor Yellow
pip install -e . -q
Write-Host "   ✓ 'kurt' command available" -ForegroundColor Green
Write-Host ""

# ── .env setup ───────────────────────────────────────────────
$KURT_DIR = "$env:USERPROFILE\.kurt"
$KURT_ENV = "$KURT_DIR\.env"
if (-not (Test-Path $KURT_ENV)) {
    New-Item -ItemType Directory -Force -Path $KURT_DIR | Out-Null
    Copy-Item "$SCRIPT_DIR\.env.example" $KURT_ENV
    Write-Host "📝 Created $KURT_ENV — lagyan mo ng API keys!" -ForegroundColor Green
    Write-Host "   Required: OPENROUTER_API_KEY"
    Write-Host "   Free keys: GOOGLE_AI_KEY, GROQ_API_KEY"
} else {
    Write-Host "📝 $KURT_ENV already exists — skipped" -ForegroundColor Green
}
Write-Host ""

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "   Next steps:"
Write-Host "   1. Edit $KURT_ENV — lagyan ng API keys"
Write-Host "   2. kurt chat          — start chatting"
Write-Host "   3. kurt do 'open Chrome'  — computer use"
Write-Host "   4. kurt voice         — voice-only mode"
Write-Host ""
Write-Host "   Sa loob ng kurt chat:"
Write-Host "   /claude <prompt>   — Claude Code CLI"
Write-Host "   /gemini <prompt>   — Gemini CLI"
Write-Host "   /gh <command>      — GitHub CLI"
Write-Host "   /help              — lahat ng commands"
Write-Host ""
