#!/bin/bash
# ============================================================
# KURT v3.0 — One-command setup
# Run once after cloning: bash install_deps.sh
#
# LAHAT ng tools nasa project folder — walang global installs!
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "🤖 Setting up K.U.R.T. — Kinetic Unified Response Terminal"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Node / npm tools (Claude Code CLI, Gemini CLI) ──────────
echo "📦 Installing npm tools (Claude Code CLI, Gemini CLI)..."
if command -v node &>/dev/null; then
    npm install --prefix "$SCRIPT_DIR"
    echo "   ✓ node_modules/ created — lahat naka-local sa project"
else
    echo "   ⚠  Node.js not found. Install from: https://nodejs.org"
    echo "   ⚠  Skipping Claude Code CLI + Gemini CLI"
fi
echo ""

# ── Python deps ──────────────────────────────────────────────
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt --break-system-packages -q
echo "   ✓ requirements.txt installed"
echo ""

# ── Playwright browser ───────────────────────────────────────
echo "🌐 Installing Playwright browser (for web automation)..."
python -m playwright install chromium 2>/dev/null && echo "   ✓ Chromium installed" || echo "   ⚠  Playwright chromium skipped (run: playwright install chromium)"
echo ""

# ── KURT itself ──────────────────────────────────────────────
echo "⚙️  Installing KURT CLI..."
pip install -e . --break-system-packages -q
echo "   ✓ 'kurt' command available"
echo ""

# ── .env setup ───────────────────────────────────────────────
KURT_ENV="$HOME/.kurt/.env"
if [ ! -f "$KURT_ENV" ]; then
    mkdir -p "$HOME/.kurt"
    cp "$SCRIPT_DIR/.env.example" "$KURT_ENV"
    echo "📝 Created ~/.kurt/.env — lagyan mo ng API keys!"
    echo "   Required: OPENROUTER_API_KEY"
    echo "   Free keys: GOOGLE_AI_KEY, GROQ_API_KEY"
else
    echo "📝 ~/.kurt/.env already exists — skipped"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete!"
echo ""
echo "   Next steps:"
echo "   1. Edit ~/.kurt/.env — lagyan ng API keys"
echo "   2. kurt chat          — start chatting (Hey Kurt voice active)"
echo "   3. kurt do 'buksan ang Safari'  — computer use"
echo "   4. kurt voice         — voice-only mode"
echo ""
echo "   Sa loob ng kurt chat:"
echo "   /claude <prompt>   — Claude Code CLI"
echo "   /gemini <prompt>   — Gemini CLI"
echo "   /gh <command>      — GitHub CLI"
echo "   /help              — lahat ng commands"
echo ""
