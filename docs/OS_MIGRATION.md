# Moving Kurt between computers and operating systems

Windows is the first migration target (user decision November 18, 2026).
Cloud GPU hosting and offline model/CLI expansion remain parked.

Voice update: the default bootstrap now includes `web,media,voice`, with
WebRTC speech detection and online Groq transcription, without local model
weights. Use `--features web,media` for the smaller typed-only profile. See
[Tagalog/Taglish voice](TAGALOG_VOICE.md) for audio upload behavior, vocabulary,
F5 conversation and current testing limits. Older setup notes below describe
the original optional-voice checkpoint.

## One command from GitHub and private credential transfer

Requires Python 3.10+ on Windows. Once this installer is published to `main`,
run this single line in Windows PowerShell (Git is not required):

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/vic2reyhilario080780/kurt-ai/main/Install-GitHub.ps1')))
```

It resolves `main` to an immutable commit, downloads that source archive and
installs into `%LOCALAPPDATA%\Kurt`. It refuses to overwrite an existing
installation; use `-InstallDir 'C:\another-folder\Kurt'` for a different fresh
location. It downloads source from your public repository, never the real
`.env`. As with running any installer script, only run the URL for a repository
you trust. Actual Windows execution remains pending native verification.

To avoid entering each of your own provider keys again, first export your
iMac's `.env` through a hidden passphrase prompt:

```sh
kurt device export-credentials ~/Downloads/kurt-private.kurt-credentials
```

Use a strong transfer passphrase of at least 12 characters. If cryptography is
missing, install the `migration` extra first. Copy the encrypted file privately
to Windows Downloads, then use this **single install-and-import command**:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/vic2reyhilario080780/kurt-ai/main/Install-GitHub.ps1'))) -CredentialsFile "$HOME\Downloads\kurt-private.kurt-credentials"
```

Enter the one transfer passphrase when prompted. The bootstrap installs the
crypto extra and decrypts locally into this owner's `~/.kurt/.env`; API keys
are not transmitted to GitHub. Fernet authenticated encryption uses a random
salt and PBKDF2-HMAC-SHA256 (1,200,000 iterations). Wrong passwords and modified
files fail before writing. Existing configured keys are preserved by default;
explicit `kurt device import-credentials FILE --replace` replaces matching
values. Imported `.env` values remain local plaintext, as in Kurt's existing
personal setup, under the OS user's profile permissions. Account-specific
URLs/paths may still need adjustment. CLI OAuth/keychain sessions are separate.

Encrypted backups are ignored by Git and kept outside source/installer bundles.
This flow is only for **your own computers**. Do not distribute provider keys
or their encrypted owner backup to SaaS users. SaaS uses the existing private
wallet/provider gateway and per-user/device tokens. That gateway still needs
deployment; this installer does not provision or enable it automatically.
GPU hosting and offline expansion remain parked.

Crypto reference: [cryptography's authenticated Fernet and password-based key derivation](https://cryptography.io/en/latest/fernet/).

## What is ready in source

- One stdlib bootstrap chooses Windows `Scripts` or macOS/Linux `bin` paths and
  installs into the project's `.venv`. No global pip or system-Python overrides.
- Windows double-click `Install Kurt.cmd` / `Start Kurt.cmd`; macOS
  `Install Kurt.command` / `Start Kurt.command`; Linux shell wrappers.
- Default dependencies are core + web + image verification. Voice, desktop,
  npm AI CLIs and Chromium downloads are explicit options, not prerequisites
  for API chat. No local AI model downloads.
- Peekaboo is an optional npm dependency because the upstream package only
  supports macOS. A Windows npm install must not fail trying to install it.
- `kurt device status` reports OS/CPU, installed libraries/binaries and known
  limitations without authenticating providers or running paid inference.
- Preference export/import excludes credentials and machine-specific state.
- Windows bounded subprocess output uses pipe-reading threads, not selectors
  that only support Windows sockets. Timeouts request child-process-tree
  termination. Known npm `.cmd` launchers resolve to their package's JS
  entrypoint and native Node executable; prompts remain argv values and never
  become shell commands.
- The picker and `/cli default|use` block known unsupported adapters before
  selection. Copilot/DeepSeek's current read-only adapters require macOS
  enforcement; other CLI accounts/runtime behavior still need Windows tests.

These are **source-based installers with a Python prerequisite**, not signed,
self-contained `.exe`/MSI installers. An actual Windows machine is still
required to verify double-click startup, audio, native dependencies and CLIs.
The added CI workflow contains Windows/macOS/Linux smoke jobs; writing the
workflow does not mean the hosted jobs have run or passed.

## First move: iMac to Windows

1. On the iMac, export the preferences:

   ```sh
   kurt device export-settings kurt-settings.json
   ```

2. Get a source copy containing these changes onto Windows. Exclude
   `node_modules`, `.venv`, `.env`, `~/.kurt`, caches and generated build output.
   Do not copy macOS binaries or virtual environments onto Windows. Uncommitted
   source changes are not available from a fresh GitHub clone until published.

3. Install Python 3.10+ with its launcher from
   [python.org](https://www.python.org/downloads/). Open the project folder and
   double-click **Install Kurt.cmd**. This downloads the default Python
   dependencies into `.venv`; internet is needed for initial installation.

4. In a terminal opened in the project folder, configure this device:

   ```powershell
   .\.venv\Scripts\python.exe -m kurt.main device import-settings .\kurt-settings.json
   .\.venv\Scripts\python.exe -m kurt.main setup
   .\.venv\Scripts\python.exe -m kurt.main device status
   ```

5. Double-click **Start Kurt.cmd**. Sign in to the CLIs you choose, reconnect
   apps, and grant Windows microphone/desktop permissions when needed.

The `.venv` Python path avoids changing PowerShell execution policy or relying
on another `kurt` command already installed globally. For ordinary commands,
use `.\.venv\Scripts\python.exe -m kurt.main <command>` from this project.

To add optional features later, run the installer again with selected options:

```powershell
py -3 bootstrap.py --features web,media,voice,desktop
py -3 bootstrap.py --browser
py -3 bootstrap.py --cli-tools
```

`--browser` downloads Chromium. `--cli-tools` requires Node.js/npm and installs
the project's supported npm packages locally; missing Vibe/DeepSeek/Codex
packages are not silently installed by that switch. Consult each CLI's setup.
Video verification needs an available `ffprobe` executable (from FFmpeg).
Voice uses separately configured online speech services; OS audio libraries
and permissions can still be required.

## What moves and what stays device-specific

| Exported | Configure separately on the new computer |
| --- | --- |
| User/Kurt name, theme, icon, language, greeting and voice preference | API keys, CLI login, OAuth/MCP connections and browser login |
| Chat, CLI, image and video default choices | Installed applications, CLI packages, Python/Node dependencies |
| Compact/routing display preferences | Local project paths/files, conversation databases, tasks/schedules |
| | Wallet enablement, service URL and private device token |

Import merges only explicitly portable fields into the target persona. It
keeps that device's keys, wallet state and project references untouched.
A missing/unsupported selected CLI becomes `auto` with a visible warning.
Model availability/credits are not tested by importing preferences. The JSON
export contains personal names/greetings, so share it only as intended.

## macOS and Linux

From a fresh source copy with Python 3.10+:

```sh
bash install_deps.sh
.venv/bin/python -m kurt.main device import-settings kurt-settings.json
.venv/bin/python -m kurt.main setup
.venv/bin/python -m kurt.main device status
.venv/bin/python -m kurt.main chat
```

On Linux, Python's `venv` package may need installation through the distro
package manager. X11/Wayland, audio libraries, permissions and sandbox support
affect desktop features. Generic service execution still fails closed on
Linux; Codex has its separate upstream permission adapter and needs its own
native readiness test. A successful API chat install does not verify desktop
automation or identical capabilities across platforms.

## Verification and follow-up

Run `python bootstrap.py --dry-run` before installing to inspect downloads and
paths. The portability tests exercise settings round trips, rejection of
untrusted fields, missing CLI fallback, Windows launcher resolution and
bounded output/timeout behavior. A clean macOS virtual environment successfully
installed `.[web,media]`, passed `pip check`, loaded CLI help/device commands
and ran the portability suite. No real Windows/Linux host was used in this
development session. Signed installers, bundled Python, Windows desktop
automation parity and equivalent kernel isolation remain follow-up work.
