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
- 🎤 **Tagalog/Taglish voice** — F5 conversation, shared Groq speech credentials, custom vocabulary and unclear-speech handling. [Setup, upload behavior and testing limits](docs/TAGALOG_VOICE.md).

## 🚀 Quick Start

### Install

```bash
# Fresh source copy (Python 3.10+ required)
git clone https://github.com/vic2reyhilario080780/kurt-ai.git
cd kurt-ai

# macOS / Linux: project-local .venv
bash install_deps.sh

# Windows: double-click Install Kurt.cmd, then Start Kurt.cmd.
# Or use PowerShell:
.\install_deps.ps1

# Optional: python bootstrap.py --features web,media,voice,desktop --cli-tools --browser
```

For moving to another computer, start with the
[Windows-first migration guide](docs/OS_MIGRATION.md). Export/import portable
preferences with `kurt device`; API keys, logins and local project paths are
configured separately. Python 3.10+ is currently required. Cloud GPU hosting
and offline expansion are parked.

Windows one-command source installation (after Python is installed):

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/vic2reyhilario080780/kurt-ai/main/Install-GitHub.ps1')))
```

For your own second computer, append `-CredentialsFile` with the path to your
private `.kurt-credentials` export and enter its transfer passphrase once.
Provider keys are never committed or downloaded from GitHub; SaaS clients
use the private gateway/token flow instead. See the migration guide for the
complete owner-transfer command.

### Import API keys mula sa USB — Windows

Kapag installed na si Kurt, isaksak ang USB na may
`kurt-private.kurt-credentials`. Kopyahin ito sa **PowerShell**:

```powershell
& "$env:LOCALAPPDATA\Kurt\.venv\Scripts\python.exe" -m kurt.main device import-credentials ((Read-Host 'I-paste ang buong path ng credential file sa USB, halimbawa E:\kurt-private.kurt-credentials').Trim().Trim('"'))
```

Sa File Explorer, right-click ang encrypted file → **Copy as path**, saka
i-paste kapag tinanong ng command. Tinatanggap din ang path na may quotes o
spaces. Ilagay ang transfer password kapag tinanong, pagkatapos isara at
buksan ulit si Kurt. Hindi kailangang kopyahin ang file sa Downloads.

Ito ay para sa default GitHub installation sa `%LOCALAPPDATA%\Kurt` at sa
sarili mong encrypted credential export, hindi raw `.env`. Kung iba ang
installation folder, palitan ang Python path sa command. Kung may missing
`cryptography` dependency, patakbuhin muna:

```powershell
& "$env:LOCALAPPDATA\Kurt\.venv\Scripts\python.exe" -m pip install 'cryptography>=43'
```

**Windows note:** code-execution tools (`bash`, `run_code`, the coding agent
workbench) use a lexical pre-flight guard on Windows instead of the macOS
kernel-level sandbox — real protection against commands that reference
credential paths, but not an equivalent guarantee. See the docstring in
`kurt/utils/execution.py` for details.

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

Sa `kurt chat`, piliin ang **`/models`** para sa buong OpenRouter at fal.ai
catalogs: **All models**, categories na tugma ang totals, search, official model
pages, at compatible default actions. Available rin ang full-catalog links sa
chat/image/video settings pickers. Use `/models refresh` para mag-update at
`/models routing` para sa routing rules. [Catalog guide](docs/MODEL_CATALOGS.md).
May optional BYOK catalogs din para sa Hugging Face, Together, Fireworks,
Replicate, WaveSpeed at Novita. Kapag pumili ng model, may masked API-key input
at official key/login-page link bago i-confirm ang selection. [BYOK guide](docs/BYOK_PROVIDERS.md).

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

### Hosted subscription foundation

`kurt cloud status`, `kurt cloud ask`, and `kurt cloud run` connect explicitly to the hosted API. See [SaaS architecture, isolation controls and deployment requirements](docs/SAAS_FOUNDATION.md). The foundation is locally tested; billing, client sign-in and live Linux isolation verification remain required before a paid launch.

### Coding workbench

Use `kurt code "fix the failing tests" --cwd /path/to/repo` for scoped read/edit/test work, or add `--backend codex` for explicit delegation to your installed Codex CLI. See [coding capabilities, verification and limits](docs/CODING_WORKBENCH.md).
