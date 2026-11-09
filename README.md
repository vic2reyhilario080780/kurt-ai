# 🤖 KURT — Personal AI Orchestrator

> **Isang command. Lahat ng AI.** Auto-routes sa pinaka-tamang model depende sa task mo.

```
kurt "gumawa ng snake game"       → DeepSeek Coder (best for code)
kurt "research viral products"    → Gemini Flash (best for research)  
kurt "i-translate ito sa English" → LLaMA 3.3 (fastest for translation)
kurt "gumawa ng TikTok script"    → Claude Haiku (best for writing)
```

## ✨ Features

- 🧠 **Auto-routing** — Hindi mo na kailangang pumili ng model, KURT mismo ang magdedecide
- 🌐 **10+ AI Providers** — ChatGPT, Claude, Gemini, Groq, DeepSeek, LLaMA, Mistral, at iba pa
- 💸 **Free-first** — Prioritizes libre na models (OpenRouter free tier, Gemini 1,500/day, Groq 14,400/day)
- 🧠 **Skills System** — Domain expertise: TikTok, SEO, trading, e-commerce, Filipino, game dev
- 🔌 **Plugins System** — Feature packs: web search, code runner, PDF reader, Shopee, Lazada
- 💾 **Memory** — SQLite-based conversation history, pwedeng i-continue ang session
- 📡 **Streaming** — Real-time output, hindi kailangang maghintay
- 🏠 **Offline Mode** — Ollama fallback para kahit walang internet
- 📊 **Native data library** — 10,000 skills, 10,000 declared workflow agents, and 10,000 executable plugin recipes for CSV/JSON analysis. These are metric/domain specializations of ten shared operations. [Usage, scope and validation](docs/NATIVE_LIBRARY.md).
- 🖥️ **Desktop CLI orchestration** — OpenClaw task delegation and Peekaboo app/screen/mouse/keyboard commands through chat, the AI agent, or `kurt cli`. [Setup and examples](docs/DESKTOP_CLI.md).

## 🚀 Quick Start

### Install

```bash
# Option 1: pip (recommended)
pip install kurt-ai

# Option 2: pipx (isolated environment)
pipx install kurt-ai

# Option 3: from source
git clone https://github.com/daddytito/kurt-ai
cd kurt-ai
pip install -e .
```

### Setup (one-time lang)

```bash
kurt setup
```

Mag-aask ito ng API keys isa-isa may direct link para kumuha.

**Minimum requirement:** OpenRouter API key lang (libre, 1 key = lahat ng models)

### Gamitin na!

```bash
# Basic usage
kurt "explain quantum computing sa simple words"

# Code tasks → auto-routes to DeepSeek Coder
kurt "gumawa ng snake game sa Python"

# Research → auto-routes to Gemini Flash
kurt "research best skincare products 2025 Philippines"

# TikTok content with skill
kurt --skill tiktok "gumawa ng script about sunscreen"

# Interactive chat mode
kurt chat

# Force specific model
kurt --model gpt-4o "review my business plan"

# Verbose mode (see routing decisions)
kurt -v "solve this math problem: integrate x^2 + 3x"
```

## 📋 All Commands

| Command | Description |
|---------|-------------|
| `kurt "task"` | Main command — auto-routes to best model |
| `kurt setup` | Interactive setup wizard |
| `kurt models` | List all models + status |
| `kurt chat` | Interactive chat mode |
| `kurt skill list` | Show all skills |
| `kurt skill install path.json` | Install custom skill |
| `kurt plugin list` | Show all plugins |
| `kurt plugin enable <id>` | Enable a plugin |
| `kurt mcp list` | List MCP connections |

## 🧠 Skills (Domain Expertise)

Skills ay sistema ng knowledge na nag-guide sa AI behavior para sa specific na tasks.

```bash
# List lahat ng available skills
kurt skill list

# Use a skill
kurt --skill tiktok "gumawa ng 60-sec script about coffee"
kurt --skill seo "audit this website: example.com"
kurt --skill trading "analyze BTC/USDT chart pattern"
kurt --skill ecommerce "write Shopee listing for wireless earbuds"
kurt --skill filipino "ano ang pwedeng negosyo sa Pilipinas?"
```

### Built-in Skills

| ID | Name | Best For |
|----|------|----------|
| `tiktok` | TikTok Viral Formula | Scripts, hooks, captions |
| `copywriting` | Copywriting Expert | Sales copy, landing pages |
| `seo` | SEO Expert | Keywords, on-page SEO |
| `trading` | Crypto Trading Analyst | TA, signals, risk management |
| `filipino` | Filipino Language Expert | Taglish, local context |
| `game-dev` | Game Developer | pygame, HTML5, ASCII games |
| `ecommerce` | E-Commerce Expert | Shopee PH, Lazada listings |

### Create Custom Skill

```bash
# Generate template
kurt skill create my-skill

# Edit the generated my-skill.json, then install
kurt skill install my-skill.json
```

## 🔌 Plugins (Feature Packs)

```bash
kurt plugin list
kurt plugin enable web-scraper
kurt plugin enable pdf-reader
kurt plugin disable voice
```

## 🤖 AI Routing Logic

KURT automatically picks the best model per task type:

| Task Type | Best Model | Why |
|-----------|-----------|-----|
| `CODE` | DeepSeek Coder (via OpenRouter free) | Best code quality |
| `GAME` | DeepSeek Coder | Game logic + code |
| `RESEARCH` | Gemini Flash (free) | 1M context, web-aware |
| `MATH` | DeepSeek R1 | Reasoning specialist |
| `WRITE` | Claude Haiku | Best prose quality |
| `TRANSLATE` | LLaMA 3.3 (Groq) | Fast, multilingual |
| `CHAT` | LLaMA 3.3 70B (Groq) | Speed + quality |
| `IMAGE` | fal.ai Flux Schnell | Fast, affordable |
| `MUSIC` | Replicate MusicGen | Audio generation |

### Free Tier Priority

1. **OpenRouter free** — LLaMA 3.3, Gemini, DeepSeek (`:free` suffix)
2. **Google AI Studio** — Gemini Flash (1,500 req/day)
3. **Groq** — LLaMA 3.3 70B, DeepSeek R1 (14,400 req/day)
4. **DeepSeek** — $2 free credits ($0.014/1M tokens)
5. **Paid fallback** — OpenAI, Anthropic, Mistral
6. **Offline** — Ollama (local models)

## ⚙️ Configuration

Config file: `~/.kurt/.env`

```env
OPENROUTER_API_KEY=sk-or-v1-...  # Required!
GROQ_API_KEY=gsk_...             # Free, 14,400 req/day
GOOGLE_AI_KEY=AIzaSy...          # Free, 1,500 req/day
DEEPSEEK_API_KEY=sk-...          # $2 free credits
```

## 🔗 Getting API Keys (all FREE to start!)

| Provider | Free Tier | Link |
|----------|-----------|------|
| **OpenRouter** | Free models available | https://openrouter.ai/keys |
| Google AI Studio | 1,500 req/day | https://aistudio.google.com/apikey |
| Groq | 14,400 req/day | https://console.groq.com/keys |
| DeepSeek | $2 credits | https://platform.deepseek.com/api_keys |
| OpenAI | $5 credits | https://platform.openai.com/api-keys |
| Anthropic | $5 credits | https://console.anthropic.com/settings/keys |

## 🗺️ Roadmap

- [x] v0.1 — Core CLI + routing + skills + plugins
- [ ] v0.2 — MCP connectors (Gmail, Notion, GitHub, Shopee, GCash)
- [ ] v0.3 — Voice mode (speech-to-text + TTS)
- [ ] v0.4 — Web scraping + research agent
- [ ] v0.5 — Custom agents (TikTok agent, Shopee agent)
- [ ] v1.0 — Full MCP marketplace

## 📄 License

MIT License — Free to use, modify, distribute.

---

Made with ❤️ para sa mga Pinoy developers ni **Daddy Tito**
