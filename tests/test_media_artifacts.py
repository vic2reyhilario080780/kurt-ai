import asyncio
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from PIL import Image

from kurt.core import media_artifacts as artifacts, persona, execution_preferences as prefs
from kurt.core.assistant_tools import invoke_assistant
from kurt.capabilities.bridge import NativeToolRouter


class MediaArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for obj, name, value in [(artifacts, 'OUTPUT_DIR', self.root/'output'),
                                 (persona, 'KURT_DIR', self.root), (persona, 'PERSONA_PATH', self.root/'persona.json')]:
            context = patch.object(obj, name, value); context.start(); self.addCleanup(context.stop)

    def download(self, response):
        real_client = httpx.Client
        with patch('kurt.core.media_artifacts.httpx.Client', lambda **kw: real_client(transport=httpx.MockTransport(lambda request: response), **kw)):
            return artifacts.finalize_artifact('https://v3b.fal.media/file.png', 'image')

    def test_404_html_and_signature_only_image_are_not_completed(self):
        for response in [httpx.Response(404, text='Specified object does not exist'),
                         httpx.Response(200, headers={'content-type': 'text/html'}, text='<html>error</html>'),
                         httpx.Response(200, content=b'\x89PNG\r\n\x1a\n')]:
            with self.subTest(response=response), self.assertRaises(Exception): self.download(response)
        self.assertFalse(list((self.root/'output').glob('*.part')))

    def test_real_image_saved_and_receipt_written(self):
        stream = io.BytesIO(); Image.new('RGB', (2, 2), 'blue').save(stream, format='PNG')
        receipt = self.download(httpx.Response(200, content=stream.getvalue(), headers={'content-type': 'image/png'}))
        self.assertTrue(receipt['file_verified'])
        self.assertFalse(receipt['content_verified'])
        self.assertEqual(Path(receipt['path']).read_bytes(), stream.getvalue())
        self.assertTrue(Path(receipt['path']+'.json').exists())

    def test_redirect_to_unapproved_host_blocked(self):
        with self.assertRaisesRegex(ValueError, 'approved provider'):
            self.download(httpx.Response(302, headers={'location': 'https://private.example/file.png'}))

    def test_video_requires_real_stream_and_duration(self):
        file = self.root/'video.mp4'; file.write_bytes(b'not a video')
        with self.assertRaises(RuntimeError): artifacts.probe_file(file, 'video')

    def test_real_synthetic_video_download_and_stream_verification(self):
        import shutil
        import subprocess
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            self.skipTest('ffmpeg/ffprobe unavailable')
        source = self.root/'fixture.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=32x32:d=0.2',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True, capture_output=True)
        real_client = httpx.Client
        with patch('kurt.core.media_artifacts.httpx.Client', lambda **kw: real_client(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=source.read_bytes(), headers={'content-type': 'video/mp4'})), **kw)):
            receipt = artifacts.finalize_artifact('https://v3b.fal.media/fixture.mp4', 'video')
        self.assertTrue(receipt['file_verified'])
        self.assertGreater(receipt['duration_seconds'], 0)
        self.assertFalse(receipt['has_audio'])
        self.assertFalse(receipt['content_verified'])

    def test_hallucinated_media_link_never_streams_to_user(self):
        class Planner:
            supports_native_tools = True
            async def route(self, **kwargs):
                yield 'Rendered na! https://v3b.fal.media/'
                yield 'invented.mp4'
        async def run():
            return ''.join([c async for c in NativeToolRouter(Planner()).route('mistral', 'test', [{'role': 'user', 'content': 'Create a video'}])])
        answer = asyncio.run(run())
        self.assertIn('Walang verified generation receipt', answer)
        self.assertNotIn('invented.mp4', answer)

    def test_reference_cannot_be_silently_dropped_or_default_changed(self):
        prefs.save_default_media('video', 'fal-ai/kling-video/v3/standard/text-to-video', 'fal')
        token = artifacts.REFERENCE_IMAGES.set(('data:image/png;base64,aGVsbG8=',))
        self.addCleanup(artifacts.REFERENCE_IMAGES.reset, token)
        with patch('kurt.core.router.ModelRouter') as router:
            router.return_value._has_key.return_value = True
            for params in [{}, {'reference_image': 0}]:
                result = invoke_assistant('generate_media', {'kind': 'video', 'prompt': 'Animate this photo', **params})
                self.assertEqual(result['status'], 'blocked')
            router.return_value.route.assert_not_called()
        self.assertTrue(prefs.media_target('video')['model'].endswith('/text-to-video'))

    def test_image_to_video_sends_exact_reference_and_does_not_retry_404(self):
        model = 'fal-ai/kling-video/v3/standard/image-to-video'
        prefs.save_default_media('video', model, 'fal')
        image = 'data:image/png;base64,aGVsbG8='
        token = artifacts.REFERENCE_IMAGES.set((image,)); self.addCleanup(artifacts.REFERENCE_IMAGES.reset, token)
        requests = []; real_client = httpx.AsyncClient
        def provider(request):
            requests.append(request)
            return httpx.Response(200, json={'video': {'url': 'https://v3b.fal.media/deleted.mp4'}})
        with patch.dict('os.environ', {'FAL_API_KEY': 'synthetic'}, clear=True), \
             patch('kurt.core.router.httpx.AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(provider), **kw)), \
             patch.object(artifacts, 'finalize_artifact', side_effect=RuntimeError('HTTP 404')):
            result = invoke_assistant('generate_media', {'kind': 'video', 'prompt': 'Say I love you', 'reference_image': 0})
        self.assertEqual(result['status'], 'unverified'); self.assertFalse(result['retry_safe'])
        self.assertEqual(len(requests), 1)
        self.assertEqual(json.loads(requests[0].content)['start_image_url'], image)
        self.assertIsNone(artifacts.FAL_REFERENCE.get())
        self.assertNotIn('Na-download', artifacts.completion_text(result))


if __name__ == '__main__': unittest.main()
