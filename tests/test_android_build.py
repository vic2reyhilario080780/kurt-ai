import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import httpx
from kurt.core import android_build as android
from kurt.utils.workspace import workspace
from kurt.capabilities.bridge import NativeToolRouter, function_schemas
from kurt.core.router import NativeToolArgumentsError


class AndroidTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.scope = workspace(self.root); self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)

    def doctor(self):
        return {'status': 'ready', 'project': str(self.root), 'sdk': str(self.root/'sdk'), 'jdk': str(self.root/'jdk')}

    def test_missing_project_wrapper_is_explicit(self):
        with patch.object(android, '_sdk', return_value=None), patch.object(android, '_jdk', return_value=None):
            result = android.android_doctor()
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(len(result['blockers']), 3)

    def test_profile_keeps_generic_protections_and_limits_process_info(self):
        profile = android.android_profile(self.root, self.root/'sdk')
        self.assertIn('(deny network*)', profile)
        self.assertIn('(deny mach-lookup)', profile)
        self.assertIn('(deny process-info*)', profile)
        self.assertIn('(allow process-info* (target self))', profile)
        self.assertIn('.ssh', profile)
        self.assertIn('(deny file-write*)', profile)

    def test_build_is_offline_and_requires_verified_output(self):
        (self.root/'gradlew').touch()
        artifact = self.root/'app/build/outputs/apk/debug/app-debug.apk'
        def run(argv, *args, **kwargs):
            self.assertIn('--offline', argv)
            self.assertIn(':app:assembleDebug', argv)
            self.assertFalse(kwargs['network'])
            artifact.parent.mkdir(parents=True); artifact.write_bytes(b'fixture')
            return {'status': 'completed', 'exit_code': 0}
        with patch.object(android, 'android_doctor', return_value=self.doctor()), patch.object(android, '_run', side_effect=run), \
             patch.object(android, '_artifact', return_value={'signature_verified': True, 'path': str(artifact)}):
            result = android.android_build()
        self.assertEqual(result['status'], 'completed')

    def test_stale_artifact_cannot_prove_build_success(self):
        (self.root/'gradlew').touch()
        path = self.root/'app/build/outputs/bundle/release/app-release.aab'
        path.parent.mkdir(parents=True); path.write_bytes(b'old')
        with patch.object(android, 'android_doctor', return_value=self.doctor()), patch.object(android, '_run', return_value={'status': 'completed'}):
            result = android.android_build(kind='aab', variant='release')
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['artifacts'], [])

    def test_existing_verified_artifact_is_up_to_date_not_new_build(self):
        (self.root/'gradlew').touch()
        path = self.root/'app/build/outputs/apk/debug/app-debug.apk'
        path.parent.mkdir(parents=True); path.write_bytes(b'fixture')
        with patch.object(android, 'android_doctor', return_value=self.doctor()), \
             patch.object(android, '_run', return_value={'status': 'completed'}), \
             patch.object(android, '_artifact', return_value={'signature_verified': True, 'path': str(path)}):
            result = android.android_build()
        self.assertEqual(result['status'], 'up_to_date')
        self.assertFalse(result['artifacts'][0]['fresh'])

    def test_invalid_package_not_accepted(self):
        path = self.root/'bad.apk'
        with zipfile.ZipFile(path, 'w') as z: z.writestr('fake', 'fake')
        with self.assertRaises(ValueError):
            android._artifact(path, 'apk', self.root, self.root, self.root)

    def test_paths_and_module_injection_rejected(self):
        for module in ('../other', ':app:publish', 'app;id'):
            with self.assertRaises(ValueError): android.android_build(module=module)
        with self.assertRaises(ValueError): android.generate_qr('https://example.com/app.apk', '../escape.png')
        with self.assertRaises(ValueError): android.generate_qr('file:///etc/passwd')
        with tempfile.TemporaryDirectory() as other:
            (self.root/'link').symlink_to(other, target_is_directory=True)
            with self.assertRaises(ValueError): android.android_doctor('link')

    def test_unsigned_bundle_reports_false(self):
        path = self.root/'unsigned.aab'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('BundleConfig.pb', b'config'); z.writestr('base/manifest/AndroidManifest.xml', b'manifest')
        with patch.object(android, '_run', return_value={'status': 'completed', 'stdout': 'jar is unsigned.'}):
            receipt = android._artifact(path, 'aab', self.root, self.root, self.root)
        self.assertFalse(receipt['signature_verified'])
        self.assertEqual(len(receipt['sha256']), 64)

    def test_tools_have_native_schemas(self):
        schemas = {t['function']['name']: t['function']['parameters'] for t in function_schemas()}
        self.assertEqual(schemas['android_build']['properties']['timeout']['maximum'], 1800)
        self.assertNotIn('fetch_dependencies', schemas['android_build']['properties'])
        self.assertIn('generate_qr', schemas)


class ArgumentRecoveryTests(unittest.TestCase):
    def run_chunks(self, router):
        messages = [{'role': 'user', 'content': 'run tests'}]
        async def collect():
            return ''.join([c async for c in NativeToolRouter(router)._chunks('test', 'test', messages, {'native_tools': function_schemas()})])
        return asyncio.run(collect()), messages

    def test_reject_then_correct_once(self):
        class Router:
            count = 0
            async def route(self, **kwargs):
                self.count += 1
                if self.count == 1: raise NativeToolArgumentsError('invalid')
                yield 'corrected'
        router = Router()
        result, messages = self.run_chunks(router)
        self.assertEqual(result, 'corrected')
        self.assertEqual(router.count, 2)
        self.assertIn('seconds, not milliseconds', messages[-1]['content'])

    def test_provider_schema_rejection_is_recoverable(self):
        class Router:
            count = 0
            async def route(self, **kwargs):
                self.count += 1
                if self.count == 1:
                    response = httpx.Response(400, json={'error': {'code': 'tool_use_failed'}}, request=httpx.Request('POST', 'https://example.com'))
                    response.raise_for_status()
                yield 'corrected'
        self.assertEqual(self.run_chunks(Router())[0], 'corrected')

    def test_repeated_bad_response_stops(self):
        class Router:
            count = 0
            async def route(self, **kwargs):
                self.count += 1
                raise NativeToolArgumentsError('invalid')
                yield ''
        router = Router()
        with self.assertRaises(NativeToolArgumentsError): self.run_chunks(router)
        self.assertEqual(router.count, 2)

    def test_no_retry_after_partial_output(self):
        class Router:
            count = 0
            async def route(self, **kwargs):
                self.count += 1
                yield 'partial'
                raise NativeToolArgumentsError('invalid')
        router = Router()
        with self.assertRaises(NativeToolArgumentsError): self.run_chunks(router)
        self.assertEqual(router.count, 1)


if __name__ == '__main__': unittest.main()
