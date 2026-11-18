"""Keep Unicode CLI output usable on Windows consoles and redirected pipes."""
import sys


def configure_windows_output():
    if sys.platform != 'win32': return
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):
            try: stream.reconfigure(encoding='utf-8',errors='backslashreplace')
            except (OSError,ValueError): pass
