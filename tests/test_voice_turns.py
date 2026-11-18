"""Voice turn boundaries and handoff, without opening a real microphone."""

import asyncio
import io
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
import unittest

import numpy as np
from rich.console import Console

from kurt.core import wake_word as voice
from kurt.core.voice_activity import SpeechEndpoint, SpeechLimitReached, VoiceSettings
from kurt.core.voice_input import VoiceInputBridge


class EndpointTests(unittest.TestCase):
    def test_silence_does_not_start_a_turn(self):
        endpoint = SpeechEndpoint(VoiceSettings(start_timeout=1))
        results = [endpoint.feed(0.01) for _ in range(32)]
        self.assertEqual(results[-1], "idle")
        self.assertFalse(endpoint.started)

    def test_short_click_is_not_speech(self):
        endpoint = SpeechEndpoint(VoiceSettings())
        for p in ([0.95] * 2 + [0.01] * 10) * 5:
            endpoint.feed(p)
        self.assertFalse(endpoint.started)

    def test_pause_and_resumption_keep_the_same_utterance(self):
        endpoint = SpeechEndpoint(VoiceSettings())
        for _ in range(20):
            endpoint.feed(0.9)
        for _ in range(30):  # 960 ms pause, below the 1.5-second endpoint.
            self.assertNotEqual(endpoint.feed(0.01), "complete")
        for _ in range(10):
            endpoint.feed(0.9)
        outcomes = [endpoint.feed(0.01) for _ in range(47)]
        self.assertEqual(outcomes[-1], "complete")

    def test_long_speech_is_not_cut_at_twelve_seconds(self):
        endpoint = SpeechEndpoint(VoiceSettings())
        for _ in range(650):  # >20 seconds of continuous speech.
            self.assertNotEqual(endpoint.feed(0.9), "complete")
        with self.assertRaises(SpeechLimitReached):
            for _ in range(2000):
                endpoint.feed(0.9)


class CaptureTests(unittest.TestCase):
    def capture(self, samples, **kwargs):
        state = {"reads": 0, "aborts": 0, "closes": 0}
        class Stream:
            def __init__(self, **kw): pass
            def start(self): pass
            def abort(self, **kwargs): state['aborts'] += 1
            def close(self, **kwargs): state['closes'] += 1
            def read(self, count):
                index = state["reads"]
                state["reads"] += 1
                level = samples[index] if index < len(samples) else 0.0
                return np.full((count, 1), level, dtype=np.float32), False
        writer = Mock(return_value="fixture.wav")
        real_stream = voice._input_stream
        with patch.object(voice, '_input_stream', lambda sd, rate, **kw: real_stream(SimpleNamespace(InputStream=Stream), rate)), \
             patch.object(voice, "_write_audio", writer):
            result = voice.record_until_silence(speech_detector=lambda a: .95 if float(a[0, 0]) > 0 else .01,
                                                start_timeout=1, **kwargs)
        return result, writer, state

    def test_silence_never_creates_wav_or_transcription(self):
        result, writer, state = self.capture([0.0] * 40)
        self.assertIsNone(result)
        writer.assert_not_called()
        self.assertLess(state["reads"], 40)
        self.assertEqual(state['aborts'], 1)
        self.assertEqual(state['closes'], 1)

    def test_quiet_speech_is_not_rejected_by_the_old_volume_threshold(self):
        result, writer, _ = self.capture([.001] * 30 + [0.0] * 50)
        self.assertEqual(result, "fixture.wav")
        writer.assert_called_once()

    def test_clip_keeps_speech_longer_than_twelve_seconds(self):
        result, writer, _ = self.capture([.001] * 580 + [0.0] * 50)
        self.assertEqual(result, "fixture.wav")
        chunks, rate = writer.call_args.args
        self.assertGreater(sum(len(c) for c in chunks) / rate, 18)

    def test_cancel_discards_capture_without_fixed_recording_fallback(self):
        with patch.object(voice, "record_audio") as fallback:
            result, writer, _ = self.capture([.01] * 20, should_cancel=lambda: True)
        self.assertIsNone(result)
        writer.assert_not_called()
        fallback.assert_not_called()

    def test_capture_error_never_falls_back_to_partial_recording(self):
        with patch.object(voice, '_input_stream', side_effect=OSError), \
             patch.object(voice, "record_audio") as fallback:
            result = voice.record_until_silence(speech_detector=lambda a: .9)
        self.assertIsNone(result)
        fallback.assert_not_called()


class ListenerTurnTests(unittest.TestCase):
    def listener(self, callback=None, deferred=True):
        listener = voice.WakeWordListener(callback=callback, deferred=deferred, use_hotkey=False)
        listener._running = True
        return listener

    def test_deferred_turn_waits_for_the_matching_response_acknowledgment(self):
        callback = Mock()
        listener = self.listener(callback)
        first = voice.VoiceEvent("first")
        listener._fire_command(first)
        self.assertTrue(listener._busy())
        listener._fire_command(voice.VoiceEvent("second"))
        callback.assert_called_once()
        listener.finish_turn(first.turn_id + 1)
        self.assertTrue(listener._busy())
        listener.finish_turn(first.turn_id)
        self.assertFalse(listener._busy())

    def test_synchronous_callback_failure_releases_the_turn(self):
        listener = self.listener(Mock(side_effect=RuntimeError("test failure")), deferred=False)
        listener._fire_command(voice.VoiceEvent("hello"))
        self.assertFalse(listener._busy())

    def test_f5_uses_existing_worker_and_stop_invalidates_queued_turn(self):
        listener = self.listener(Mock())
        with patch.object(voice, "speak"), patch.object(voice.threading, "Thread") as thread:
            listener._start_conversation_mode()
            self.assertTrue(listener.is_in_conversation_mode())
            event = voice.VoiceEvent("hello")
            listener._fire_command(event)
            listener._stop_conversation_mode()
            self.assertFalse(listener.is_current_turn(event.turn_id))
            self.assertFalse(listener._turn_busy.is_set())
            thread.assert_not_called()

    def test_stop_phrase_is_local_and_is_not_sent_to_ai(self):
        callback = Mock()
        listener = self.listener(callback)
        listener._conversation_mode = True
        with patch.object(voice, "record_until_silence", return_value="test.wav"), \
             patch.object(voice, "transcribe_utterance", return_value=SimpleNamespace(text="Tigil muna.",review_reasons=())), \
             patch.object(voice, "_cleanup"), patch.object(voice, "speak"):
            listener._capture_command("f5-conversation")
        self.assertFalse(listener.is_in_conversation_mode())
        callback.assert_not_called()

    def test_busy_listener_does_not_open_microphone(self):
        listener = self.listener()
        listener._turn_busy.set()
        def stop(_): listener._running = False
        with patch.object(voice.time, "sleep", side_effect=stop), \
             patch.object(voice, "record_audio") as wake, patch.object(voice, "record_until_silence") as command:
            listener._listen_loop()
        wake.assert_not_called()
        command.assert_not_called()

    def test_conversation_mode_does_not_run_wake_word_capture(self):
        listener = self.listener()
        listener._conversation_mode = True
        def capture(origin):
            self.assertEqual(origin, "f5-conversation")
            listener._running = False
        with patch.object(listener, "_capture_command", side_effect=capture), \
             patch.object(voice, "record_audio") as wake:
            listener._listen_loop()
        wake.assert_not_called()

    def test_two_queued_tts_calls_remain_serial_and_keep_guard_until_both_finish(self):
        started = [threading.Event(), threading.Event()]
        release = [threading.Event(), threading.Event()]
        done = [threading.Event(), threading.Event()]
        def play(text, preset):
            index = int(text)
            started[index].set()
            release[index].wait(2)
            done[index].set()
        with patch.object(voice, "_speak_sync", side_effect=play):
            try:
                voice.speak("0", blocking=False, voice_preset={})
                self.assertTrue(started[0].wait(1))
                voice.speak("1", blocking=False, voice_preset={})
                self.assertTrue(voice._tts_speaking.is_set())
                self.assertFalse(started[1].is_set())
                release[0].set()
                self.assertTrue(started[1].wait(1))
                self.assertTrue(voice._tts_speaking.is_set())
            finally:
                for event in release: event.set()
                for event in done: event.wait(2)
                deadline = time.monotonic() + 2
                while voice._tts_speaking.is_set() and time.monotonic() < deadline:
                    time.sleep(.005)
        self.assertFalse(voice._tts_speaking.is_set())


class PromptHandoffTests(unittest.IsolatedAsyncioTestCase):
    async def test_voice_interrupts_real_prompt_without_enter_and_preserves_typed_draft(self):
        from prompt_toolkit.input.defaults import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        from kurt.core import command_palette as palette
        real_session = palette.PromptSession
        bridge = VoiceInputBridge()
        event = voice.VoiceEvent("Kumusta", turn_id=1)
        console = Console(file=io.StringIO())
        with create_pipe_input() as pipe, \
             patch.object(palette, "_session", None), patch.object(palette, "_state", None), \
             patch.object(palette.sys if hasattr(palette, 'sys') else __import__('sys'), "stdin") as stdin:
            stdin.isatty.return_value = True
            with patch.object(palette, "PromptSession", lambda **kw: real_session(input=pipe, output=DummyOutput(), **kw)):
                task = asyncio.create_task(asyncio.to_thread(palette.read_chat_input, console, voice_input=bridge))
                try:
                    await asyncio.sleep(.08)
                    pipe.send_text("unfinished draft")
                    await asyncio.sleep(.05)
                    bridge.submit(event)
                    result = await asyncio.wait_for(task, 2)
                    self.assertIs(result, event)
                    second = asyncio.create_task(asyncio.to_thread(palette.read_chat_input, console, voice_input=bridge))
                    await asyncio.sleep(.05)
                    pipe.send_text("\r")
                    self.assertEqual(await asyncio.wait_for(second, 2), "unfinished draft")
                finally:
                    pipe.send_text("\x03")

    async def test_voice_arriving_before_prompt_bind_is_not_lost(self):
        bridge = VoiceInputBridge()
        event = voice.VoiceEvent("hello")
        bridge.submit(event)
        app = SimpleNamespace(is_done=False, current_buffer=SimpleNamespace(text=""), exit=Mock(), invalidate=Mock())
        bridge.bind(app, asyncio.get_running_loop())
        await asyncio.sleep(0)
        app.exit.assert_called_once()
        self.assertIs(bridge.pop(), event)
        bridge.unbind()


class ChatVoiceTurnTests(unittest.TestCase):
    def test_chat_waits_through_tts_and_releases_on_success_error_and_slash(self):
        from kurt import main
        for utterance, answer in (("hello", "Kumusta!"), ("hello", None), ("/model auto", "unused")):
            trace = []
            listener = voice.WakeWordListener(use_hotkey=False)
            listener._running = True
            listener._conversation_mode = True
            called = False
            def start(callback, **kwargs):
                self.assertTrue(kwargs["deferred"])
                listener.on_command(callback, deferred=True)
                return listener
            def read(console, *, voice_input):
                nonlocal called
                if not called:
                    called = True
                    listener._fire_command(voice.VoiceEvent(utterance))
                    self.assertTrue(listener._busy())
                    trace.append("submitted")
                    return voice_input.pop()
                self.assertFalse(listener._busy())
                trace.append("ready")
                return "/exit"
            async def respond(**kwargs):
                self.assertTrue(listener._busy())
                trace.append("thinking")
                return answer
            def speak(*args, **kwargs):
                self.assertTrue(kwargs["blocking"])
                self.assertTrue(listener._busy())
                self.assertEqual(listener.state, "speaking")
                trace.append("speaking")
            console = Console(file=io.StringIO())
            with self.subTest(utterance=utterance, answer=answer), \
                 patch.object(main, "console", console), patch.object(main, "load_env"), \
                 patch.object(main, "load_persona", return_value={}), \
                 patch("kurt.core.persona.load_persona", return_value={}), \
                 patch.object(main.sys.stdin, "isatty", return_value=True), \
                 patch.object(main.sys.stdout, "isatty", return_value=False), \
                 patch.object(main, "read_chat_input", side_effect=read), \
                 patch.object(main, "stream_response", side_effect=respond), \
                 patch.object(voice, "check_dependencies", return_value={"can_record": True, "can_transcribe": True, "can_detect_speech": True}), \
                 patch.object(voice, "start_listening", side_effect=start), \
                 patch.object(voice, "stop_listening", side_effect=listener.stop), \
                 patch.object(voice, "speak", side_effect=speak), \
                 patch("kurt.persona.KurtPersona") as persona_mock, \
                 patch.dict("sys.modules", {"kurt.core.screen_watcher": None}):
                persona_mock.return_value.build.return_value = {"system_prompt": "test", "temperature": .5}
                main.chat(skill=None, model=None, cli=None, session="test", no_memory=True)
            self.assertEqual(trace[0], "submitted")
            self.assertEqual(trace[-2:], ["speaking", "ready"])


if __name__ == "__main__":
    unittest.main()
