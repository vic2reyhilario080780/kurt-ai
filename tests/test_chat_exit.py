import asyncio
from contextlib import ExitStack
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput
from rich.console import Console
from kurt.core import command_palette as palette


class ExitKeyboardTests(unittest.IsolatedAsyncioTestCase):
    async def test_exit_after_deleting_slash_and_inside_nested_picker(self):
        real_session = palette.PromptSession
        for keys, expected in [('/\x7fexit\r', 'exit'), ('/cli\rexit\r', '/exit'), ('/setting\r\x15exit\r', 'exit')]:
            with self.subTest(keys=keys), create_pipe_input() as pipe, \
                 patch.object(palette.engine, 'PromptSession', lambda **kw: real_session(input=pipe, output=DummyOutput(), **kw)):
                session, state = palette._build_session()
                task = asyncio.create_task(session.prompt_async())
                try:
                    await asyncio.sleep(.03)
                    pipe.send_text(keys)
                    self.assertEqual(await asyncio.wait_for(task, 2), expected)
                    self.assertFalse(state.is_open)
                finally:
                    if not task.done(): task.cancel()


class ChatCleanupTests(unittest.TestCase):
    def test_every_exit_path_stops_resources_without_ai_or_goodbye_tts(self):
        from kurt import main
        from kurt.core import wake_word as voice
        for incoming in ('exit', '/exit', '/quit', EOFError(), KeyboardInterrupt(), RuntimeError('input failed')):
            with self.subTest(incoming=repr(incoming)), ExitStack() as stack:
                listener, proactive = Mock(), Mock()
                stack.enter_context(patch.object(main, 'console', Console(file=io.StringIO())))
                stack.enter_context(patch.object(main, 'load_env'))
                stack.enter_context(patch.object(main, 'load_persona', return_value={}))
                stack.enter_context(patch('kurt.core.persona.load_persona', return_value={}))
                stack.enter_context(patch.object(main.sys.stdin, 'isatty', return_value=True))
                stack.enter_context(patch.object(main.sys.stdout, 'isatty', return_value=False))
                read = stack.enter_context(patch.object(main, 'read_chat_input'))
                if isinstance(incoming, BaseException): read.side_effect = incoming
                else: read.return_value = incoming
                stack.enter_context(patch.object(voice, 'check_dependencies', return_value={'can_record': True, 'can_transcribe': True, 'can_detect_speech': True}))
                stack.enter_context(patch.object(voice, 'start_listening', return_value=listener))
                stop = stack.enter_context(patch.object(voice, 'stop_listening'))
                speak = stack.enter_context(patch.object(voice, 'speak'))
                browser = stack.enter_context(patch.object(main, 'close_browser_session'))
                ai = stack.enter_context(patch.object(main, 'stream_response'))
                stack.enter_context(patch.dict('sys.modules', {'kurt.core.screen_watcher': SimpleNamespace(KURTProactive=Mock(return_value=proactive))}))
                if isinstance(incoming, RuntimeError):
                    with self.assertRaises(RuntimeError): main.chat(prompt=None, skill=None, model=None, cli=None, session='test', no_memory=True, verbose=False)
                else:
                    main.chat(prompt=None, skill=None, model=None, cli=None, session='test', no_memory=True, verbose=False)
                stop.assert_called_once()
                proactive.stop.assert_called_once()
                browser.assert_called_once()
                ai.assert_not_called()
                speak.assert_not_called()


if __name__ == '__main__': unittest.main()
