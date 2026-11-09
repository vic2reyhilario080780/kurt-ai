"""Bounded argv-only subprocess execution with process-group timeout cleanup."""
import os
import selectors
import signal
import subprocess
import tempfile
import time


def run_bounded(argv, *, env, cwd, timeout=180, input_text=None, max_output=1024*1024):
    with tempfile.TemporaryFile() as source:
        if input_text is not None:
            source.write(input_text.encode()); source.seek(0)
        process = subprocess.Popen(argv, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   cwd=cwd, env=env, start_new_session=True)
        stdout, stderr = bytearray(), bytearray()
        status, deadline = 'completed', time.monotonic()+timeout
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, stdout)
                selector.register(process.stderr, selectors.EVENT_READ, stderr)
                while selector.get_map():
                    remaining=deadline-time.monotonic()
                    if remaining<=0:
                        status='timed_out';break
                    for key,_ in selector.select(min(remaining,0.25)):
                        chunk=os.read(key.fileobj.fileno(),8192)
                        if not chunk:
                            selector.unregister(key.fileobj);continue
                        if len(stdout)+len(stderr)+len(chunk)>max_output:
                            status='output_limit';break
                        key.data.extend(chunk)
                    if status!='completed':break
            if status=='completed':
                process.wait(timeout=max(0.01,deadline-time.monotonic()))
                if process.returncode: status='failed'
        except subprocess.TimeoutExpired:
            status='timed_out'
        finally:
            if process.poll() is None or status in ('timed_out','output_limit'):
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            process.wait(timeout=5)
            process.stdout.close();process.stderr.close()
    return {'status':status,'exit_code':process.returncode,'stdout':stdout.decode(errors='replace'),
            'stderr':stderr.decode(errors='replace'),'truncated':status=='output_limit'}
