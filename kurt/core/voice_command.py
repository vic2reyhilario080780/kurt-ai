"""Standalone `kurt voice` ("Hey Kurt") command — extracted from kurt/main.py
for size and maintainability.

Shared state is reached through `kurt.main` explicitly (`main.NAME`) rather
than imported directly, for the same reason documented in chat_loop.py: it
keeps existing `unittest.mock.patch.object(main, "NAME", ...)` test patches
working unchanged after this move.
"""
import asyncio
import uuid

import typer
from rich import box
from rich.panel import Panel

from kurt.utils.security import redact


def run_voice(model, speak, hotkey_only):
    import kurt.main as main

    main.load_env()
    main.init_db()

    _persona = main.load_persona()
    _kurt_name = _persona.get("kurt_name", "KURT")
    session_id = str(uuid.uuid4())
    from kurt.core.execution_preferences import ExecutionSession, run_default_cli, CLIQuotaExhausted
    try:
        voice_execution = ExecutionSession.load(model=model if isinstance(model, str) else None)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


    main.console.print(Panel(
        f"[bold cyan]🎤 {_kurt_name} — Voice Mode[/bold cyan]\n"
        "[dim]Press F5 for hands-free conversation; Ctrl+Shift+K for one turn.\n"
        "'Hey Kurt' needs a cached local wake recognizer.\n"
        "Press Ctrl+C to exit[/dim]",
        box=box.ROUNDED, border_style="cyan"
    ))

    from kurt.core.speech_recognition import options as speech_options
    if speech_options()['provider']=='groq':
        main.console.print('[dim]Online voice: activated audio goes to Groq and may use credits. Background wake detection stays local.[/dim]')

    # Check voice dependencies
    try:
        from kurt.core.wake_word import check_dependencies, start_listening, speak as kurt_speak
        deps = check_dependencies()

        if not deps.get("can_record"):
            main.console.print("[yellow]⚠ Microphone not available. Install: pip install sounddevice soundfile[/yellow]")
            main.console.print("[dim]Running in hotkey-only mode (Ctrl+Shift+K)[/dim]")
            hotkey_only = True

        if not deps.get("can_transcribe"):
            main.console.print("[yellow]⚠ Speech recognition unavailable. Configure Groq in /setup and check kurt speech status, or use an existing cached local model.[/yellow]")
            if not hotkey_only:
                main.console.print("[red]Cannot run voice mode without STT.[/red]")
                return

        if deps.get("can_detect_speech") is False:
            main.console.print("[red]Speech detection unavailable. Install the voice extra (webrtcvad-wheels); no local AI model download is needed.[/red]")
            return

    except ImportError:
        main.console.print("[red]❌ Voice module not available.[/red]")
        return

    voice_history=[]
    from kurt.persona import KurtPersona
    voice_persona = KurtPersona()

    def remember_voice(user,answer):
        voice_history.extend([{'role':'user','content':user},{'role':'assistant','content':answer}])
        del voice_history[:-24]

    def handle_voice_command(event):
        """Process a voice command through Kurt's AI"""
        text = event.text.strip()
        if not text:
            return

        main.console.print(f"\n[bold cyan]You[/bold cyan] [dim](voice)[/dim]: {text}")

        direct_action = main._try_local_request(text, session_id)
        if direct_action is not None:
            remember_voice(text,direct_action['message'])
            if speak:
                kurt_speak(direct_action['message'], blocking=True)
            return

        # Unmatched speech uses the same goal-directed tool planner as chat.
        analysis = voice_execution.analysis()

        persona_turn = voice_persona.build(text, mode="auto", include_history=False)
        messages = [
            {"role": "system", "content": persona_turn["system_prompt"]},
            {"role": "system", "content": (
                f"You are {_kurt_name}, a voice assistant. "
                "Prefer concise responses suitable for text-to-speech; give the full "
                "derivation or detail when the user requests it. "
                + main.get_language_system_prompt()
            )},
            *voice_history,
            {"role": "user", "content": text},
        ]

        # F5 uses chat directly; standalone voice follows the same saved defaults.
        try:
            if voice_execution.cli != "auto" and not voice_execution.exhausted:
                full_response = run_default_cli(voice_execution.cli, messages)
            else:
                full_response = asyncio.run(main.stream_response(analysis, messages, session_id, True, False,
                                                           prompt=text, execution=voice_execution,
                                                           temperature=persona_turn["temperature"])) or "Request incomplete."
        except CLIQuotaExhausted:
            voice_execution.exhausted = True
            full_response = "CLI quota exhausted. Auto routing is enabled for the next request; the current task was not replayed."
        except (ValueError, OSError, RuntimeError) as exc:
            full_response = f"Selected CLI failed: {redact(str(exc))[:500]}. Task was not replayed."

        main.console.print(f"\n[bold green]🤖 {_kurt_name}[/bold green]: {full_response}")

        remember_voice(text,full_response)

        if speak and full_response:
            from kurt.core.wake_word import strip_markdown_for_speech
            kurt_speak(strip_markdown_for_speech(full_response), blocking=True)

        main.save_message(session_id, "user", text)
        main.save_message(session_id, "assistant", full_response)

    # Start the voice listener
    main.console.print("[dim]Starting voice listener...[/dim]")
    try:
        from kurt.core.wake_word import start_listening, speak as kurt_speak
        listener = start_listening(callback=handle_voice_command,hotkey_only=hotkey_only)
        from kurt.core.speech_recognition import status as speech_status
        details=speech_status()
        route='Groq online speech: activated audio is uploaded and may use credits.' if details['provider']=='groq' else 'Cached local speech.'
        main.console.print(f"[green]✓ Voice mode active![/green] [dim]{route} F5 to talk; wake word needs a cached local model.[/dim]")
        kurt_speak(f"{_kurt_name} voice ready. Press F5 para makipag-usap.", blocking=False)

        # Keep running
        import time
        while True:
            time.sleep(0.5)

    except KeyboardInterrupt:
        main.console.print("\n[dim]Voice mode stopped.[/dim]")
        try:
            from kurt.core.wake_word import stop_listening
            stop_listening()
        except Exception:
            pass
    except Exception as e:
        main.console.print(f"[red]❌ Voice mode error: {e}[/red]")
