import os
from pathlib import Path
import shutil
import pty
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check-omp-load.py'


class OmpLoadIsolationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('omp'), 'installed OMP required; pre-push load gate checks availability')
    def test_load_ignores_persistent_home_agent_and_runtime_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            agent = home / 'agent'
            agent.mkdir()
            (agent / 'models.yml').write_text('invalid: [\n')
            (agent / 'config.yml').write_text('invalid: [\n')
            env = {'PATH': os.environ.get('PATH', os.defpath), 'HOME': directory,
                   'PI_CODING_AGENT_DIR': str(agent), 'PI_PROXY': 'invalid-proxy',
                   'PI_PACKAGE_DIR': '/nonexistent', 'PI_SMOL_MODEL': 'real-model-must-not-be-used',
                   'OMP_PROFILE': 'must-not-be-used'}
            before = {str(path): (path.read_bytes(), path.stat().st_mtime_ns)
                      for path in home.rglob('*') if path.is_file()}
            result = subprocess.run([sys.executable, '-B', str(SCRIPT)], env=env, capture_output=True,
                                    text=True, timeout=35)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('no model turn', result.stdout)
            self.assertEqual({str(path): (path.read_bytes(), path.stat().st_mtime_ns)
                              for path in home.rglob('*') if path.is_file()}, before)

    @unittest.skipUnless(shutil.which('omp'), 'installed OMP required; pre-push load gate checks availability')
    def test_load_completes_when_stdin_is_a_terminal(self):
        # An interactive caller (an OMP pty shell, a developer's terminal) leaves stdin attached to a
        # tty; OMP's RPC mode then waits on it unless the probe closes it.
        leader, follower = pty.openpty()
        try:
            result = subprocess.run([sys.executable, '-B', str(SCRIPT)], stdin=follower,
                                    capture_output=True, text=True, timeout=35)
        finally:
            os.close(follower)
            os.close(leader)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('no model turn', result.stdout)
