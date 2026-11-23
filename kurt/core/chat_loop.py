"""Interactive `kurt chat` loop — extracted from kurt/main.py for size and
maintainability.

Shared state (console, load_env, stream_response, etc.) is reached through
`kurt.main` explicitly (`main.NAME`) rather than imported directly — a plain
`from kurt.main import NAME` would bind an independent copy at import time,
which `unittest.mock.patch.object(main, "NAME", ...)` in the existing test
suite would no longer reach. Referencing `main.NAME` at call time preserves
those patches unchanged after this move.
"""
import asyncio
import select
import sys
import time
import uuid

import typer
from rich import box
from rich.live import Live
from rich.panel import Panel

from kurt.core.cli_orchestrator import handle_slash, SLASH_COMMANDS
from kurt.skills.manager import get_skill_prompt
from kurt.utils.security import redact


def run_chat(prompt, skill, model, cli, session, no_memory, verbose):
    import kurt.main as main

    main.load_env()
    if not no_memory:
        main.init_db()

    _persona = main.load_persona()
    _kurt_name = _persona.get("kurt_name", "KURT")
    _icon = main.get_icon()
    _theme = main.get_theme()

    session_id = session if session else str(uuid.uuid4())
    from kurt.core.execution_preferences import ExecutionSession, run_default_cli, CLIQuotaExhausted
    try:
        execution = ExecutionSession.load(model=model, cli=cli if isinstance(cli, str) else None)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    current_model = execution.model
    current_skill = skill
    last_response = ""
    session_images = None  # Latest attachment group retained only in RAM.
    conversation = []  # Session context is retained even when disk memory is off.
    _pending_initial = prompt.strip() if isinstance(prompt, str) and prompt.strip() else None

    from kurt.persona import KurtPersona
    kurt_persona = KurtPersona()

    # ── Welcome banner — Kurt's own startup screen ───────────────────
    from kurt import __version__ as _kurt_version

    # ── Voice mode (Hey Kurt) ────────────────────────────────────────
    # Wire in background voice listener — injects voice commands as if typed
    from kurt.core.voice_input import VoiceInputBridge
    _voice_input_bridge = VoiceInputBridge()
    _voice_active = False
    _voice_listener = None
    try:
        from kurt.core.wake_word import start_listening, check_dependencies as _voice_deps
        _deps = _voice_deps() if sys.stdin.isatty() else {}
        if _deps.get("can_record") and _deps.get("can_transcribe") and _deps.get("can_detect_speech", False):
            from kurt.core.speech_recognition import options as speech_options
            if speech_options()['provider']=='groq':
                main.console.print('[dim]Online voice: activated audio goes to Groq and may use credits. Background wake detection stays local.[/dim]')
            _voice_listener = start_listening(callback=_voice_input_bridge.submit, deferred=True,
                                              state_callback=_voice_input_bridge.set_status)
            _voice_active = True
    except Exception:
        pass  # Voice is optional; typed chat remains available.

    def _voice_reply(text):
        if not _from_voice or not _voice_active or not text:
            return
        if _voice_event is not None and not _voice_listener.is_current_turn(_voice_event.turn_id):
            return
        from kurt.core.wake_word import speak, strip_markdown_for_speech
        _voice_listener._set_state("speaking")
        try:
            speak(strip_markdown_for_speech(text), blocking=True)
        except Exception:
            main.console.print("[yellow]Voice playback failed; the response is available above.[/yellow]")

    def _render_banner(phase: float) -> Panel:
        return Panel(
            main._kurt_welcome_banner(
                kurt_name=_kurt_name,
                kurt_version=_kurt_version,
                theme=_theme,
                user_name=main.get_user_name(),
                current_model=execution.status(),
                current_skill=current_skill,
                session_id=session_id,
                phase=phase,
                defaults=_persona,
            ),
            box=box.ROUNDED,
            border_style=_theme.get("border", "cyan"),
            style=_theme.get("background", ""),
        )

    def _glow_until_keypress(render_fn, fps=18):
        """Keep the banner glowing/pulsing in place for as long as you sit there
        — stops the instant you press a key. Puts stdin in cbreak mode (no
        line buffering, no local echo) just for this idle wait: `select` peeks
        at stdin without consuming bytes, and with echo off the terminal
        driver never prints a keystroke mid-redraw. Settings are restored
        before handing off to the normal chat prompt either way."""
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            frame_dt = 1.0 / fps
            phase = 0.0
            with Live(render_fn(0.0), console=main.console, refresh_per_second=fps) as live:
                while True:
                    if _voice_input_bridge.has_pending or (_voice_listener and _voice_listener.is_in_conversation_mode()):
                        break
                    ready, _, _ = select.select([sys.stdin], [], [], frame_dt)
                    if ready:
                        break
                    phase = (phase + frame_dt * 0.35) % 1.0
                    live.update(render_fn(phase))
        except KeyboardInterrupt:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    if sys.stdin.isatty() and sys.stdout.isatty():
        if sys.platform != "win32":
            try:
                _glow_until_keypress(_render_banner)
            except Exception:
                main.console.print(_render_banner(0.0))
        else:
            # cbreak/select can't watch stdin this way on Windows — short
            # intro loop instead of an indefinite idle glow.
            with Live(_render_banner(0.0), console=main.console, refresh_per_second=18) as _glow:
                for _i in range(1, 25):
                    _glow.update(_render_banner(_i / 24))
                    time.sleep(0.045)
    else:
        main.console.print(_render_banner(0.0))

    if _voice_active:
        from kurt.core.speech_recognition import status as speech_status
        _speech=speech_status()
        _route='Groq online speech (activated audio is uploaded; may use credits)' if _speech['provider']=='groq' else 'cached local speech'
        _wake="'Hey Kurt' or " if _speech['cached_local_model'] else ''
        main.console.print(f"[dim]🎤 {_route} — {_wake}F5 to talk hands-free. Say 'tigil muna' to pause.[/dim]\n")

    # ── Screen watcher (proactive mode) ─────────────────────────────
    try:
        from kurt.core.screen_watcher import KURTProactive
        _proactive = KURTProactive() if sys.stdin.isatty() else None
        if _proactive:
            _proactive.start()
    except Exception:
        _proactive = None

    try:
        while True:
            _from_voice = False
            _voice_event = None
            if _pending_initial is not None:
                prompt = _pending_initial
                _pending_initial = None
                main.console.print(f"\n[bold cyan]You[/bold cyan] [dim]›[/dim] {prompt}")
            else:
                try:
                    incoming = (main.read_chat_input(main.console, voice_input=_voice_input_bridge)
                                if _voice_active else main.read_chat_input(main.console))
                    if isinstance(incoming, str):
                        prompt = incoming.strip()
                    elif incoming is not None:
                        _voice_event = incoming
                        if not _voice_listener.is_current_turn(incoming.turn_id):
                            continue  # F5 was stopped before the queued turn was consumed.
                        prompt = incoming.text.strip()
                        _from_voice = True
                        main.console.print(f"\n[bold cyan]You[/bold cyan] [dim](🎤 voice)[/dim]: {prompt}")
                    else:
                        continue
                except (KeyboardInterrupt, EOFError):
                    main.console.print("\n[dim]👋 Bye![/dim]")
                    break

            if not prompt:
                if _voice_event is not None and _voice_listener:
                    _voice_listener.finish_turn(_voice_event.turn_id)
                continue

            try:
                if _voice_listener:
                    _voice_listener.set_processing(True)
                # Legacy text shortcuts
                if prompt.lower() in ["exit", "quit", "bye"]:
                    main.console.print("[dim]👋 Bye! K.U.R.T. signing off.[/dim]")
                    break

                if prompt.lower() == "clear":
                    session_images = None
                    conversation.clear()
                    session_id = str(uuid.uuid4())
                    main.console.print(f"[dim]🆕 New session: {session_id[:8]}[/dim]")
                    continue

                # Explicit file attachments are input data, not slash commands
                # or a keyword-based task classifier. Keep bytes out of history.
                from kurt.core.attachments import parse_image_input, load_images, image_content
                images = []
                try:
                    first = prompt.split(None, 1)[0].casefold()
                    attached = parse_image_input(prompt) if first not in SLASH_COMMANDS else None
                    if attached and attached.paths:
                        if execution.cli != "auto" and not execution.exhausted:
                            main.console.print("Image attachment recognized. This CLI adapter cannot forward image bytes. Use /cli use auto with a vision-capable chat model, or use the CLI's own image attachment flow.", markup=False)
                            continue
                        images = load_images(attached.paths)
                        names = ', '.join(img['name'] for img in images)
                        main.console.print(f"Attached image: {names}", markup=False)
                        prompt = (attached.text or 'Describe the attached image. Say clearly if details are unreadable.') + f"\n[Image attachments: {names}]"
                except (ValueError, OSError) as exc:
                    if isinstance(exc, PermissionError):
                        main.console.print("Cannot read that photo. Export it from Photos to Pictures/Desktop, then attach the exported copy.", markup=False)
                    else:
                        main.console.print(f"Image attachment failed: {redact(str(exc))}", markup=False)
                    continue

                # ── Slash command handler ────────────────────────────────────
                slash_result = handle_slash(
                    prompt="" if images else prompt,
                    session_id=session_id,
                    current_model="auto (default quota exhausted)" if execution.exhausted else current_model,
                    current_skill=current_skill,
                    last_response=last_response,
                    current_cli=execution.cli if not execution.exhausted else "auto (default exhausted)",
                )

                if slash_result.handled:
                    if slash_result.output:
                        main.console.print(slash_result.output, markup=False)
                        if slash_result.continue_chat:
                            _voice_reply(slash_result.output)
                    if prompt.lower().startswith(("/config", "/setting")):
                        _persona = main.load_persona()
                        _theme = main.get_theme()
                        _icon = main.get_icon()
                        _kurt_name = _persona.get("kurt_name", "KURT")
                    if slash_result.model_override:
                        current_model = slash_result.model_override
                        execution.model = current_model
                        execution.cli = "auto"
                        execution.exhausted = False
                        execution.exhausted_provider = None
                        main.console.print(f"[dim]Model set to: {current_model}[/dim]")
                    if slash_result.cli_override is not None:
                        execution.cli = slash_result.cli_override
                        execution.exhausted = False
                        execution.exhausted_provider = None
                    if slash_result.skill_override:
                        current_skill = slash_result.skill_override
                    if slash_result.feed_to_ai and slash_result.output:
                        # Keep the request and computed results available to follow-up turns.
                        if not no_memory:
                            main.save_message(session_id, "user", prompt)
                            main.save_message(session_id, "assistant", slash_result.output)
                        last_response = slash_result.output
                        conversation.extend([{'role': 'user', 'content': prompt},
                                             {'role': 'assistant', 'content': slash_result.output}])
                    if slash_result.new_session_id:
                        session_id = slash_result.new_session_id
                        last_response = ""
                        conversation.clear()
                        session_images = None
                    if not slash_result.continue_chat:
                        break
                    continue

                # Every ordinary conversation reaches the same semantic planner. App
                # discovery/actions are tools; no prompt keyword/regex chooses a handler.
                analysis = execution.analysis()

                messages = []

                # System prompt: KURT persona (persona.md + memory.md + mode detection)
                _persona_turn = kurt_persona.build(prompt, mode="auto", include_history=execution.cli == "auto" or execution.exhausted)
                messages.append({"role": "system", "content": _persona_turn["system_prompt"]})
                # Operational guidance — not personality, so it stays separate from persona.md.
                messages.append({"role": "system", "content": (
                    "You are running as a CLI tool called KURT — Kinetic Unified Response Terminal. "
                    "The user speaks in pure natural language (no slash commands needed). "
                    "Whenever asked about events, news, leaders, prices, weather, or developments from June 2024 to the present, "
                    "always use the `search_web` (and `read_webpage`) tool automatically so your knowledge is completely up to date."
                )})

                # Language prompt
                lang_prompt = main.get_language_system_prompt()
                if lang_prompt:
                    messages.append({"role": "system", "content": lang_prompt})

                # Skill prompt
                active_skill = current_skill
                if prompt.startswith("/skill "):
                    # Inline skill override
                    active_skill = prompt.split(None, 1)[1].strip()
                if active_skill:
                    skill_prompt = get_skill_prompt(active_skill)
                    if skill_prompt:
                        messages.append({"role": "system", "content": skill_prompt})

                # The planner chooses search/navigation from meaning; do not pre-fetch
                # URLs or trigger search from a regex before it has understood the goal.
                history = main.get_history(session_id, limit=20) if not no_memory else conversation[-20:]
                if images:
                    session_images = (prompt, images)
                history = [dict(m) for m in history]
                if session_images and not images and (execution.cli == 'auto' or execution.exhausted):
                    marker, retained = session_images
                    for previous in reversed(history):
                        if previous.get('role') == 'user' and previous.get('content') == marker:
                            previous['content'] = image_content(marker, retained)
                            break
                    else:
                        # Keep the latest reference available after history compaction.
                        history.insert(0, {'role': 'user', 'content': image_content(marker, retained)})
                messages.extend(history)
                messages.append({"role": "user", "content": image_content(prompt, images) if images else prompt})

                if not no_memory:
                    main.save_message(session_id, "user", prompt)

                main.console.print(f"\n[{_theme['primary']}]{_icon} {_kurt_name}[/{_theme['primary']}]")

                if execution.cli != "auto" and not execution.exhausted:
                    try:
                        main.console.print(f"[dim]Using CLI: {execution.cli}[/dim]")
                        with main.console.status(f"Waiting for {execution.cli} CLI…", spinner="dots"):
                            response = run_default_cli(execution.cli, messages)
                        main.console.print(response, markup=False)
                        if not no_memory and response:
                            main.save_message(session_id, "assistant", response, f"cli:{execution.cli}")
                    except CLIQuotaExhausted:
                        execution.exhausted = True
                        main.console.print("Default CLI quota exhausted → auto routing enabled for the next request. Current task was not replayed.", markup=False)
                        _voice_reply("Naubos ang CLI quota. Naka-auto na ang susunod na request; hindi ko inulit ang kasalukuyang task.")
                        conversation.extend([{"role": "user", "content": prompt},
                                             {"role": "assistant", "content": "CLI quota exhausted; task outcome unverified. Check current state before continuing."}])
                        if not no_memory:
                            main.save_message(session_id, "assistant", conversation[-1]["content"])
                        continue
                    except (ValueError, OSError, RuntimeError) as exc:
                        main.console.print(f"Default CLI failed: {redact(str(exc))[-2200:]}", markup=False)
                        main.console.print("Task was not replayed. Check the CLI/workspace, or use /cli use auto.", markup=False)
                        _voice_reply("Hindi natapos ng napiling CLI ang request. Hindi ko ito inulit; tingnan muna ang kasalukuyang resulta.")
                        receipt = "Default CLI failed; task outcome unverified. Check current state before continuing; do not automatically replay."
                        conversation.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": receipt}])
                        if not no_memory:
                            main.save_message(session_id, "assistant", receipt)
                        continue
                else:
                    response = asyncio.run(main.stream_response(
                        analysis=analysis,
                        messages=messages,
                        session_id=session_id,
                        no_memory=no_memory,
                        verbose=verbose,
                        prompt=prompt,
                        temperature=_persona_turn["temperature"],
                        execution=execution,
                    ))
                if response is None:
                    if images:
                        main.console.print("The selected model could not complete image analysis. Choose a vision-capable chat model; no image description was verified.", markup=False)
                    _voice_reply("Hindi natapos ang AI request. Nasa screen ang error; puwede mo akong kausapin ulit.")
                    receipt = "Selected AI request failed; task outcome unverified. Inspect current state before continuing."
                    conversation.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": receipt}])
                    if not no_memory:
                        main.save_message(session_id, "assistant", receipt)
                    continue
                if isinstance(response, str) and response:
                    kurt_persona.remember(prompt, response)
                    conversation.extend([{'role': 'user', 'content': prompt},
                                         {'role': 'assistant', 'content': response}])
                    last_response = response

                    _voice_reply(response)

                # Store last response for /save
                from kurt.core.memory import get_history as _gh
                _hist = _gh(session_id, limit=1) if not no_memory else []
                if _hist and _hist[-1]["role"] == "assistant":
                    last_response = _hist[-1]["content"]

            finally:
                if _voice_listener:
                    if _voice_event is not None:
                        _voice_listener.finish_turn(_voice_event.turn_id)
                    _voice_listener.set_processing(False)

    finally:
        # Every exit route releases the same resources, including /exit,
        # EOF, Ctrl+C and unexpected errors. Do not speak the goodbye on exit.
        _voice_input_bridge.unbind()
        if _proactive:
            try:
                _proactive.stop()
            except Exception:
                pass
        if _voice_listener:
            try:
                from kurt.core.wake_word import stop_listening
                stop_listening()
            except Exception:
                pass
        main.close_browser_session()
