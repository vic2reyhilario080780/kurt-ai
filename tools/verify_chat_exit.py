"""Opt-in real-terminal exit checks. Starts only owned test shells/Kurt sessions."""
import argparse
import json
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import signal
import time


def verify(command, keys, idle_seconds, cwd):
    pid, fd = pty.fork()
    if pid == 0:
        env = os.environ.copy()
        env.update(PS1='KURT_EXIT_SHELL> ', TERM='xterm-256color')
        os.chdir(cwd)
        os.execve('/bin/zsh', ['zsh', '-f'], env)

    def read_until(marker, timeout):
        data = b''
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if select.select([fd], [], [], .1)[0]:
                try: chunk = os.read(fd, 65536)
                except OSError: break
                if not chunk: break
                data += chunk
                if marker in data: return True, data
        return False, data

    try:
        ready, _ = read_until(b'KURT_EXIT_SHELL>', 5)
        os.write(fd, (shlex.join(command)+'\r').encode())
        banner, _ = read_until(b'Type your message', 25)
        time.sleep(idle_seconds)
        start = time.monotonic()
        os.write(fd, keys)
        returned, output = read_until(b'KURT_EXIT_SHELL>', 10)
        return {'passed': ready and banner and returned and b'Bye!' in output,
                'returned_to_shell': returned, 'goodbye_seen': b'Bye!' in output,
                'seconds': round(time.monotonic()-start, 2)}
    finally:
        # Only processes in this newly forked test terminal are touched.
        try:
            group = os.tcgetpgrp(fd)
            if group > 0 and group != os.getpgrp(): os.killpg(group, signal.SIGTERM)
        except OSError: pass
        os.close(fd)
        try: os.kill(pid, signal.SIGTERM)
        except ProcessLookupError: pass
        deadline = time.monotonic()+1
        while time.monotonic() < deadline:
            if os.waitpid(pid, os.WNOHANG)[0]: break
            time.sleep(.05)
        else:
            try: os.kill(pid, signal.SIGKILL)
            except ProcessLookupError: pass
            os.waitpid(pid, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--idle-seconds', type=float, default=3)
    args = parser.parse_args()
    if not 0 <= args.idle_seconds <= 20: parser.error('Idle time must be 0–20 seconds.')
    binary = shutil.which('kurt')
    if binary is None: parser.error('Installed kurt command not found.')
    cases = [('plain_exit', b'exit\r'), ('deleted_slash', b'/\x7fexit\r'),
             ('nested_picker', b'/cli\rexit\r'), ('ctrl_d', b'\x04')]
    rows = []
    # Bare kurt from home matches normal interactive use; also check explicit
    # chat, /exit and F5 conversation mode without requiring any AI response.
    for name, keys in cases:
        row = {'case': 'bare_'+name, **verify([binary], keys, args.idle_seconds, str(Path.home()))}
        rows.append(row); print(json.dumps(row), flush=True)
    for name, keys in [('slash_exit', b'/exit\r'), ('f5_exit', b'\x1b[15~exit\r')]:
        row = {'case': 'chat_'+name, **verify([binary, 'chat', '--no-memory'], keys, args.idle_seconds, str(Path.cwd()))}
        rows.append(row); print(json.dumps(row), flush=True)
    report = {'passed': all(r['passed'] for r in rows), 'idle_seconds': args.idle_seconds,
              'scope': 'Installed CLI, real zsh/PTYS, bare/home plus chat/picker/EOF/F5 cases; no model requests', 'results': rows}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
