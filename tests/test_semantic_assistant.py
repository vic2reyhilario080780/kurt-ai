import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from kurt.core.assistant_tools import invoke_assistant
from kurt.capabilities.bridge import function_schemas
from kurt.capabilities.bridge import NativeToolRouter
import asyncio


class Replies:
    supports_native_tools = True

    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    async def route(self, **kwargs):
        self.calls.append(json.loads(json.dumps(kwargs)))
        yield next(self.replies)


def call(tool, **params):
    return json.dumps({'tool': tool, 'params': params})


class SemanticAssistantTests(unittest.TestCase):
    def test_completed_previous_goal_is_not_reused_for_a_new_user_request(self):
        messages = [
            {'role': 'user', 'content': 'Show Notes'},
            {'role': 'assistant', 'content': call('set_task_goal', objective='Show Notes', goal_type='app_foreground', target_app='Notes')},
            {'role': 'user', 'content': 'NATIVE TOOL RESULT (data):\n' + json.dumps({'status': 'planned', 'goal_type': 'app_foreground', 'target_app': 'Notes'})},
            {'role': 'assistant', 'content': call('open_application', app='Notes')},
            {'role': 'user', 'content': 'NATIVE TOOL RESULT (data):\n' + json.dumps({'status': 'completed', 'app': 'Notes', 'foreground_verified': True})},
            {'role': 'user', 'content': 'Explain a text editor; do not open anything.'},
        ]
        replies = Replies(['A text editor edits documents.'])
        async def run():
            return ''.join([c async for c in NativeToolRouter(replies).route('test', 'test', messages)])
        self.assertEqual(asyncio.run(run()), 'A text editor edits documents.')
        self.assertEqual(len(replies.calls), 1)

    def test_verified_app_goal_removes_action_tools_and_cannot_click_after_completion(self):
        replies = Replies([call('set_task_goal', objective='Show Notes', goal_type='app_foreground', target_app='Notes'),
                           call('open_application', app='Notes'), call('press_key', app='Notes', key='cmd+n')])
        def invoke(name, params, paths):
            if name == 'set_task_goal':
                return {'status': 'planned', **params}
            self.assertEqual(name, 'open_application')
            return {'status': 'completed', 'app': 'Notes', 'foreground_verified': True, 'pid': 123}
        async def run():
            return ''.join([c async for c in NativeToolRouter(replies).route('test', 'test',
                [{'role': 'user', 'content': 'Ihanda ang pang notes, app lang muna.'}])])
        with patch('kurt.capabilities.bridge.invoke_native', side_effect=invoke) as invoke_tool:
            result = asyncio.run(run())
        self.assertEqual(invoke_tool.call_count, 2)
        self.assertIn('Notes', result)
        self.assertEqual(len(replies.calls), 2)  # No further model/action round after verified success.

    def test_workflow_continues_beyond_app_opening(self):
        replies = Replies([call('set_task_goal', objective='Prepare a new document', goal_type='workflow', target_app=''),
                           call('open_application', app='TextEdit'), call('press_key', app='TextEdit', key='cmd+n'),
                           'New document observed.'])
        def invoke(name, params, paths):
            if name == 'set_task_goal':
                return {'status': 'planned', **params}
            if name == 'open_application':
                return {'status': 'completed', 'app': 'TextEdit', 'foreground_verified': True}
            return {'status': 'observed_after_action', 'observation': {'window_title': 'Untitled'}}
        async def run():
            return ''.join([c async for c in NativeToolRouter(replies).route('test', 'test',
                [{'role': 'user', 'content': 'Ihanda ang isang bagong dokumento.'}])])
        with patch('kurt.capabilities.bridge.invoke_native', side_effect=invoke) as invoke_tool:
            result = asyncio.run(run())
        self.assertEqual(invoke_tool.call_count, 3)
        self.assertIn('New document', result)

    def test_an_action_requires_a_declared_goal(self):
        replies = Replies([call('open_application', app='Notes'), 'I need to declare the goal first.'])
        async def run():
            return ''.join([c async for c in NativeToolRouter(replies).route('test', 'test',
                [{'role': 'user', 'content': 'Ihanda ang pang notes.'}])])
        with patch('kurt.capabilities.bridge.invoke_native') as invoke_tool:
            asyncio.run(run())
        invoke_tool.assert_not_called()

    def test_required_tool_fields_are_in_schema_and_checked_before_dispatch(self):
        schemas = {s['function']['name']: s['function']['parameters'] for s in function_schemas(False)}
        self.assertNotIn('desktop_action', schemas)
        self.assertEqual(set(schemas['fill_field']['required']), {'app', 'element', 'text'})
        self.assertEqual(set(schemas['press_key']['required']), {'app', 'key'})
        with patch('kurt.core.desktop_actions.desktop_action') as dispatch:
            with self.assertRaisesRegex(ValueError, 'missing='):
                invoke_assistant('fill_field', {'app': 'Safari', 'text': 'hello'})
        dispatch.assert_not_called()

    def test_meaning_driven_chat_does_not_call_keyword_routes(self):
        from kurt import main
        prompt = 'May kukuwentahin akong simpleng arithmetic. Ihanda ang pangcompute.'
        replies = Replies([call('list_apps'), call('set_task_goal', objective='Prepare arithmetic app', goal_type='app_foreground', target_app='Calculator'),
                           call('open_application', app='Calculator'),
                           'Nasa harap na ang Calculator; verified ang foreground process.'])
        def invoke(name, params, paths):
            if name == 'list_apps':
                return {'status': 'completed', 'apps': ['Calculator', 'TextEdit']}
            if name == 'set_task_goal':
                return {'status': 'planned', **params}
            self.assertEqual((name, params), ('open_application', {'app': 'Calculator'}))
            return {'status': 'completed', 'app': 'Calculator', 'foreground_verified': True, 'pid': 123}
        with patch.object(main, 'load_env'), patch.object(main, 'ModelRouter', return_value=replies), \
             patch.object(main, '_try_local_request', side_effect=AssertionError('No phrase parser')), \
             patch.object(main, 'analyze_task', side_effect=AssertionError('No keyword classifier')), \
             patch('kurt.core.intent.detect_intent', side_effect=AssertionError('No keyword intent')), \
             patch('kurt.capabilities.bridge.invoke_native', side_effect=invoke) as invoke_tool:
            result = CliRunner().invoke(main.app, ['chat', '--no-memory'], input=prompt + '\nexit\n')
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(invoke_tool.call_count, 3)
        names = {s['function']['name'] for s in replies.calls[0]['native_tools']}
        self.assertTrue({'open_application', 'list_apps', 'search_web', 'run_native'} <= names)
        self.assertIn('na-verify', result.output)

    def test_disk_memory_off_preserves_context_for_followup_without_disk_writes(self):
        from kurt import main
        replies = Replies(['Calculator ang unang inihanda.', 'Babalik ako sa Calculator.'])
        with patch.object(main, 'load_env'), patch.object(main, 'ModelRouter', return_value=replies), \
             patch.object(main, 'init_db', side_effect=AssertionError('No disk memory')), \
             patch.object(main, 'save_message', side_effect=AssertionError('No disk memory')), \
             patch.object(main, 'get_history', side_effect=AssertionError('No disk memory')):
            result = CliRunner().invoke(main.app, ['chat', '--no-memory'],
                input='Ihanda ang pangcompute.\nBalik sa una.\nexit\n')
        self.assertEqual(result.exit_code, 0, result.output)
        history = replies.calls[1]['messages']
        self.assertTrue(any(m['role'] == 'user' and m['content'] == 'Ihanda ang pangcompute.' for m in history))
        self.assertTrue(any(m['role'] == 'assistant' and m['content'] == 'Calculator ang unang inihanda.' for m in history))

    def test_question_can_be_answered_without_desktop_mutations(self):
        from kurt import main
        replies = Replies(['Notes stores notes; TextEdit edits text documents.'])
        with patch.object(main, 'load_env'), patch.object(main, 'ModelRouter', return_value=replies), \
             patch('kurt.capabilities.bridge.invoke_native') as invoke:
            result = CliRunner().invoke(main.app, ['chat', '--no-memory'],
                input='Explain the difference between Notes and TextEdit.\nexit\n')
        self.assertEqual(result.exit_code, 0, result.output)
        invoke.assert_not_called()

    def test_named_interaction_tool_reuses_observed_executor(self):
        with patch('kurt.core.desktop_actions.desktop_action', return_value={'status': 'observed_after_action'}) as action:
            invoke_assistant('press_key', {'app': 'TextEdit', 'key': 'cmd+n', 'window_id': 42})
        action.assert_called_once_with('press', app='TextEdit', key='cmd+n', window_id=42)

    def test_media_creation_uses_generation_provider_and_does_not_fallback_to_text(self):
        with patch('kurt.core.router.ModelRouter') as router:
            router.return_value._has_key.return_value = False
            result = invoke_assistant('generate_media', {'kind': 'image', 'prompt': 'A blue circle'})
        self.assertEqual(result['status'], 'blocked')
        router.return_value.route.assert_not_called()

    def test_native_helper_timeout_is_unknown_outcome_and_is_not_replayed(self):
        from kurt.core import app_launcher
        with patch.object(app_launcher, 'application_paths', return_value={'notes': Path('/Applications/Notes.app')}), \
             patch.object(app_launcher.subprocess, 'run', side_effect=subprocess.TimeoutExpired('native helper', 15)) as run:
            result = app_launcher.open_installed_app('Notes')
        self.assertEqual(result['status'], 'unverified')
        self.assertEqual(run.call_count, 1)
        self.assertIn('--app', run.call_args.args[0])

    def test_unknown_app_cannot_be_passed_as_a_command_to_native_helper(self):
        from kurt.core import app_launcher
        with patch.object(app_launcher, 'application_paths', return_value={}), \
             patch.object(app_launcher.subprocess, 'run') as run:
            result = app_launcher.open_installed_app('Notes; arbitrary command')
        self.assertEqual(result['status'], 'failed')
        run.assert_not_called()
