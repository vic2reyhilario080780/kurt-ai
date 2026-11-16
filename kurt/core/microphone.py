"""macOS microphone isolation: a stuck native driver cannot trap chat shutdown.

Only the child imports sounddevice/PortAudio. The pipe contains 16 kHz mono
float32 frames, never transcripts. No provider keys are inherited by the child.
"""
import os
import selectors
import subprocess
import sys
import time

from kurt.utils.security import child_env

READY = b'KURT_MIC_READY\n'
FRAME_SIZE = 512
FRAME_BYTES = FRAME_SIZE * 4


class CaptureCancelled(RuntimeError):
    pass


class MicrophoneStream:
    def __init__(self, sample_rate=16000, should_cancel=None, *, _command=None):
        if sample_rate != 16000:
            raise ValueError('Microphone capture requires 16000 Hz.')
        self.should_cancel = should_cancel
        self.command = _command or [sys.executable, '-m', 'kurt.core.microphone', '--worker']
        self.process = None
        self.selector = None

    def _read_exact(self, count, timeout):
        data = bytearray()
        deadline = time.monotonic() + timeout
        while len(data) < count:
            if self.should_cancel and self.should_cancel():
                raise CaptureCancelled('Microphone capture cancelled.')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Microphone worker stopped delivering audio.')
            if self.selector.select(min(.1, remaining)):
                chunk = os.read(self.process.stdout.fileno(), count-len(data))
                if not chunk:
                    raise RuntimeError('Microphone worker exited before delivering audio.')
                data.extend(chunk)
        return bytes(data)

    def __enter__(self):
        try:
            self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, env=child_env(), start_new_session=True)
            self.selector = selectors.DefaultSelector()
            self.selector.register(self.process.stdout, selectors.EVENT_READ)
            if self._read_exact(len(READY), 8) != READY:
                raise RuntimeError('Invalid microphone worker handshake.')
            return self
        except BaseException:
            self.close()
            raise

    def read(self, count):
        if count != FRAME_SIZE:
            raise ValueError('Expected a 512-sample microphone frame.')
        import numpy as np
        frame = self._read_exact(1+FRAME_BYTES, 2)
        if frame[0] not in (0, 1):
            raise RuntimeError('Invalid microphone frame.')
        return np.frombuffer(frame[1:], dtype='<f4').copy().reshape(FRAME_SIZE, 1), bool(frame[0])

    def close(self):
        if self.selector is not None:
            self.selector.close()
            self.selector = None
        process, self.process = self.process, None
        if process is None:
            return
        try:
            if process.poll() is None:
                # Allow a normal abort/close first. Native driver shutdown is
                # untrusted: terminate/kill only this owned worker if it stalls.
                try:
                    process.stdin.write(b'stop\n'); process.stdin.flush()
                except (OSError, BrokenPipeError):
                    pass
                try:
                    process.wait(timeout=.35)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=.35)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=1)
        finally:
            for stream in (process.stdin, process.stdout):
                try:
                    stream.close()
                except OSError:
                    pass

    def __exit__(self, *args):
        self.close()


def _worker():
    # Keep native audio initialization and its atexit callbacks out of Kurt.
    import sounddevice as sd
    stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32')
    try:
        stream.start()
        sys.stdout.buffer.write(READY); sys.stdout.buffer.flush()
        while not selectors_readable_stdin():
            chunk, overflow = stream.read(FRAME_SIZE)
            sys.stdout.buffer.write(bytes([bool(overflow)]) + chunk.astype('<f4', copy=False).tobytes())
            sys.stdout.buffer.flush()
    finally:
        try:
            stream.abort(ignore_errors=True)
        finally:
            stream.close(ignore_errors=True)


def selectors_readable_stdin():
    import select
    return bool(select.select([sys.stdin], [], [], 0)[0])


if __name__ == '__main__':
    if sys.argv[1:] != ['--worker']:
        raise SystemExit('Internal microphone worker; use kurt chat or kurt voice.')
    _worker()
