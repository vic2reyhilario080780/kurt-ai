import os
import sys
import threading
import time
import unittest
from unittest.mock import patch

from kurt.core.microphone import CaptureCancelled, MicrophoneStream


@unittest.skipIf(sys.platform == 'win32', 'Pipe selector worker is macOS/POSIX only')
class MicrophoneProcessTests(unittest.TestCase):
    def test_real_pipe_audio_frame_and_credentials_not_inherited(self):
        code = '''import sys,struct,os
assert 'MISTRAL_API_KEY' not in os.environ
sys.stdout.buffer.write(b'KURT_MIC_READY\\n'+b'\\0'+struct.pack('<512f', *([.25]*512)))
sys.stdout.buffer.flush()
sys.stdin.readline()
'''
        with patch.dict(os.environ, {'MISTRAL_API_KEY': 'fixture-private-value'}):
            with MicrophoneStream(_command=[sys.executable, '-c', code]) as stream:
                process = stream.process
                samples, overflow = stream.read(512)
                self.assertEqual(samples.shape, (512, 1))
                self.assertAlmostEqual(float(samples[0, 0]), .25)
                self.assertFalse(overflow)
        self.assertIsNotNone(process.poll())

    def test_stuck_driver_ignoring_terminate_is_killed_and_reaped(self):
        code = '''import sys,signal,time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
sys.stdout.buffer.write(b'KURT_MIC_READY\\n');sys.stdout.buffer.flush()
time.sleep(60)
'''
        stream = MicrophoneStream(_command=[sys.executable, '-c', code])
        stream.__enter__(); process = stream.process
        start = time.monotonic()
        stream.close()
        self.assertLess(time.monotonic()-start, 2)
        self.assertIsNotNone(process.poll())
        stream.close()

    def test_cancel_interrupts_pending_audio_read_without_native_calls(self):
        code = "import sys,time;sys.stdout.buffer.write(b'KURT_MIC_READY\\n');sys.stdout.buffer.flush();time.sleep(60)"
        cancelled = threading.Event()
        with MicrophoneStream(should_cancel=cancelled.is_set, _command=[sys.executable, '-c', code]) as stream:
            timer = threading.Timer(.1, cancelled.set); timer.start()
            try:
                with self.assertRaises(CaptureCancelled): stream.read(512)
            finally:
                timer.join()

    def test_broken_startup_leaves_no_worker(self):
        stream = MicrophoneStream(_command=[sys.executable, '-c', 'pass'])
        with self.assertRaises(RuntimeError): stream.__enter__()
        self.assertIsNone(stream.process)

    def test_dependency_probe_never_imports_portaudio(self):
        from kurt.core.wake_word import check_dependencies
        with patch('importlib.util.find_spec', return_value=object()):
            before = set(sys.modules)
            result = check_dependencies()
        self.assertTrue(result['can_record'])
        self.assertFalse('sounddevice' in set(sys.modules)-before)


if __name__ == '__main__': unittest.main()
