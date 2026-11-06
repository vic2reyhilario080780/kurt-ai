#!/bin/bash
# KURT v3.0 — Install all dependencies
# Run once on Daddy Tito's iMac: bash install_deps.sh

echo "🤖 Installing KURT dependencies..."
echo ""

# Web browsing
echo "📡 Web browsing..."
pip install requests beautifulsoup4 duckduckgo-search --break-system-packages -q
echo "   ✓ requests, beautifulsoup4, duckduckgo-search"

# Playwright (full browser automation)
echo "🌐 Playwright browser automation..."
pip install playwright --break-system-packages -q
playwright install chromium 2>/dev/null || python -m playwright install chromium
echo "   ✓ playwright + chromium"

# Voice mode
echo "🎤 Voice mode (Hey Kurt)..."
pip install faster-whisper sounddevice soundfile edge-tts pyttsx3 --break-system-packages -q
echo "   ✓ faster-whisper, sounddevice, edge-tts, pyttsx3"

# Computer use
echo "🖱️  Computer use..."
pip install pyautogui Pillow --break-system-packages -q
echo "   ✓ pyautogui, Pillow"

# Hotkey listener
echo "⌨️  Hotkey..."
pip install pynput --break-system-packages -q
echo "   ✓ pynput"

echo ""
echo "✅ All done! Try:"
echo "   kurt chat       — interactive mode (Hey Kurt voice active)"
echo "   kurt voice      — voice-only mode"
echo "   kurt do 'buksan ang Safari'  — computer use"
