"""Bounded argv-only subprocess execution with process-group timeout cleanup."""
import os
import selectors
import signal
import subprocess
import tempfile
import time
import queue
import threading
import sys


def _threaded_output(process, timeout, max_output):
    """Windows selectors cannot wait on anonymous subprocess pipes."""
    items = queue.Queue(maxsize=32)
    stop = threading.Event()
    def read(stream, name):
        try:
            while not stop.is_set():
                chunk = stream.read1(8192)
                item = (name, chunk)
                while not stop.is_set():
                    try: items.put(item,timeout=.1); break
                    except queue.Full: pass
                if not chunk: break
        except (OSError,ValueError):
            pass
    threads = [threading.Thread(target=read,args=(process.stdout,'stdout'),daemon=True),
               threading.Thread(target=read,args=(process.stderr,'stderr'),daemon=True)]
    for thread in threads: thread.start()
    buffers = {'stdout':bytearray(),'stderr':bytearray()}
    ended = set(); status = 'completed'; deadline = time.monotonic()+timeout
    try:
        while len(ended)<2:
            remaining = deadline-time.monotonic()
            if remaining<=0: status='timed_out'; break
            try: name,chunk = items.get(timeout=min(.1,remaining))
            except queue.Empty: continue
            if not chunk: ended.add(name); continue
            if sum(map(len,buffers.values()))+len(chunk)>max_output:
                status='output_limit'; break
            buffers[name].extend(chunk)
        if status == 'completed':
            try: process.wait(timeout=max(.01,deadline-time.monotonic()))
            except subprocess.TimeoutExpired: status='timed_out'
    finally: stop.set()
    return status,buffers['stdout'],buffers['stderr']


def _kill_tree(process):
    if sys.platform == 'win32':
        # No shell or task text: taskkill only receives this child's numeric PID.
        from kurt.utils.security import child_env
        try:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=child_env(),timeout=5,check=False)
        except (OSError,subprocess.TimeoutExpired): pass
        if process.poll() is None: process.kill()
    else:
        try: os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError: pass


def run_bounded(argv, *, env, cwd, timeout=180, input_text=None, max_output=1024*1024):
    if sys.platform == 'win32':
        from kurt.utils.execution import windows_cli_argv
        argv = windows_cli_argv(argv)
    with tempfile.TemporaryFile() as source:
        if input_text is not None:
            source.write(input_text.encode()); source.seek(0)
        options = {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == 'win32' else {'start_new_session':True}
        process = subprocess.Popen(argv, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   cwd=cwd, env=env, **options)
        stdout, stderr = bytearray(), bytearray()
        status, deadline = 'completed', time.monotonic()+timeout
        try:
            if sys.platform == 'win32':
                status,stdout,stderr = _threaded_output(process,timeout,max_output)
                if status == 'completed' and process.returncode: status='failed'
            else:
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
                _kill_tree(process)
            process.wait(timeout=5)
            process.stdout.close();process.stderr.close()
    return {'status':status,'exit_code':process.returncode,'stdout':stdout.decode(errors='replace'),
            'stderr':stderr.decode(errors='replace'),'truncated':status=='output_limit'}
