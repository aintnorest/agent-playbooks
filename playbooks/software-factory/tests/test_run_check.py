import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run-check.py'


class RunCheckTests(unittest.TestCase):
    def test_statuses_pipefail_and_full_log(self):
        with tempfile.TemporaryDirectory() as directory:
            for command, expected, code in [('printf passed', 'passed', 0),
                                            ('printf error >&2; exit 23', 'failed', 23),
                                            ('false | cat', 'failed', 1),
                                            ('playbook_nonexistent_command_9487', 'unavailable', 127),
                                            ('sleep 10', 'timed-out', -9)]:
                with self.subTest(command=command):
                    result = subprocess.run([sys.executable, str(SCRIPT), '--command', command,
                                             '--cwd', directory, '--timeout', '0.2'],
                                            capture_output=True, text=True, timeout=5, check=True)
                    report = json.loads(result.stdout)
                    log = Path(report['logPath'])
                    try:
                        self.assertEqual(report['status'], expected)
                        self.assertEqual(report['exitCode'], code)
                        self.assertGreaterEqual(report['duration'], 0)
                        self.assertFalse(log.is_relative_to(directory))
                        self.assertEqual(report['tail'], log.read_text())
                        if expected == 'unavailable':
                            self.assertIn('not verified', report['message'])
                    finally:
                        log.unlink()
            command = "i=0; while [ $i -lt 10000 ]; do printf 'line %s\\n' $i; i=$((i+1)); done"
            report = json.loads(subprocess.check_output([sys.executable, str(SCRIPT), '--command', command,
                               '--cwd', directory, '--tail-lines', '3'], text=True))
            log = Path(report['logPath'])
            try:
                self.assertEqual(report['status'], 'passed')
                self.assertEqual(report['tail'], 'line 9997\nline 9998\nline 9999\n')
                self.assertEqual(log.read_text().splitlines(), [f'line {i}' for i in range(10000)])
            finally:
                log.unlink()

    def test_background_gate_fails_closed_and_kills_remaining_job(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'survived'
            command = f'(sleep 0.4; touch {marker}; exit 42) &'
            report = json.loads(subprocess.check_output([sys.executable, str(SCRIPT),
                               '--command', command, '--cwd', directory], text=True, timeout=5))
            try:
                self.assertEqual(report['status'], 'failed')
                self.assertEqual(report['exitCode'], 0)
                self.assertIn('foreground', report['message'])
                import time
                time.sleep(0.6)
                self.assertFalse(marker.exists(), 'background job survived gate return')
            finally:
                Path(report['logPath']).unlink()

    def test_giant_single_line_has_byte_bounded_tail_and_complete_log(self):
        import shlex
        size = 17 * 1024 * 1024
        with tempfile.TemporaryDirectory() as directory:
            command = shlex.join([sys.executable, '-c', f'import sys; sys.stdout.write("x"*{size}+"END")'])
            report = json.loads(subprocess.check_output([sys.executable, str(SCRIPT),
                               '--command', command, '--cwd', directory], text=True, timeout=10))
            log = Path(report['logPath'])
            try:
                self.assertEqual(report['status'], 'passed')
                self.assertEqual(len(report['tail'].encode()), 65536)
                self.assertTrue(report['tail'].endswith('END'))
                self.assertEqual(log.stat().st_size, size + 3)
                self.assertEqual(log.read_bytes(), b'x' * size + b'END')
            finally:
                log.unlink()

    def test_log_root_is_not_within_resolved_cwd(self):
        cwd = Path('/tmp').resolve()
        report = json.loads(subprocess.check_output([sys.executable, str(SCRIPT),
                           '--command', 'printf external', '--cwd', str(cwd)], text=True, timeout=5))
        log = Path(report['logPath']).resolve()
        try:
            self.assertEqual(report['status'], 'passed')
            self.assertFalse(log.is_relative_to(cwd))
            self.assertEqual(log.read_text(), 'external')
        finally:
            log.unlink()
