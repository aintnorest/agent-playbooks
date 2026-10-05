#!/usr/bin/env python3
"""Run a foreground project command with pipefail, bounded time, and an external log."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from git_environment import clean_git_environment

MAX_TAIL_BYTES = 64 * 1024


def run(command, cwd, timeout=120, tail_lines=40):
    started = time.monotonic()
    workspace = Path(cwd).resolve()
    # Ignore repository-controlled TMPDIR, including a cwd that is /tmp itself.
    candidates = [Path('/tmp'), Path('/var/tmp'), Path.home()] if os.name == 'posix' else [Path(tempfile.gettempdir()), Path.home()]
    log_root = next((path.resolve() for path in candidates if path.is_dir()
                     and not path.resolve().is_relative_to(workspace) and os.access(path, os.W_OK)), None)
    if log_root is None:
        raise ValueError('No writable log directory outside cwd is available.')
    child = None
    previous_handler = signal.getsignal(signal.SIGTERM)

    def terminate(_signum, _frame):
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        raise InterruptedError('Runner terminated; command process group killed.')

    signal.signal(signal.SIGTERM, terminate)
    try:
        with tempfile.NamedTemporaryFile(prefix='playbook-check-', suffix='.log', dir=log_root, delete=False) as log:
            log_path = log.name
            exit_code = None
            status = 'failed'
            message = ''
            try:
                child = subprocess.Popen(['bash', '-o', 'pipefail', '-c', command], cwd=cwd,
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                         env=clean_git_environment())
                try:
                    exit_code = child.wait(timeout=timeout)
                    status = 'passed' if exit_code == 0 else 'unavailable' if exit_code == 127 else 'failed'
                    if status == 'unavailable':
                        message = 'Command program unavailable (exit 127); not verified, not a task-code failure.'
                    try:
                        os.killpg(child.pid, 0)
                    except ProcessLookupError:
                        pass
                    else:
                        try:
                            os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        status = 'failed'
                        message = 'Background processes remained after Bash exited; group killed. Gates must run in the foreground.'
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    exit_code = child.wait()
                    status = 'timed-out'
                    message = f'Command exceeded {timeout:g}-second timeout.'
            except FileNotFoundError as error:
                status = 'unavailable' if workspace.is_dir() else 'failed'
                message = str(error)
                log.write((message + '\n').encode())
            except OSError as error:
                status = 'failed'
                if child is not None:
                    exit_code = child.wait()
                message = str(error)
                log.write((message + '\n').encode())
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
    with open(log_path, 'rb') as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - MAX_TAIL_BYTES))
        data = stream.read(MAX_TAIL_BYTES)
    tail = b''.join(data.splitlines(keepends=True)[-tail_lines:]) if tail_lines else b''
    text = tail.decode('utf-8', errors='replace').encode('utf-8')[-MAX_TAIL_BYTES:].decode('utf-8', errors='ignore')
    return dict(logPath=log_path, status=status, exitCode=exit_code, duration=time.monotonic() - started,
                tail=text, message=message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--command', required=True)
    parser.add_argument('--cwd', required=True)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--tail-lines', type=int, default=40)
    args = parser.parse_args()
    if not args.command.strip() or not math.isfinite(args.timeout) or not 0 < args.timeout <= 3600 or not 0 <= args.tail_lines <= 1000:
        parser.error('command must be non-empty, timeout in (0, 3600], and tail-lines between 0 and 1000')
    try:
        report = run(args.command, args.cwd, args.timeout, args.tail_lines)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
