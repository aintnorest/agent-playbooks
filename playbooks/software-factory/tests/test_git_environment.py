"""Inherited Git hook state must not redirect fixtures or project checks."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GitEnvironmentTests(unittest.TestCase):
    def test_poisoned_fixture_suites_and_runner_preserve_victim(self):
        clean = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        with tempfile.TemporaryDirectory(prefix='playbook-git-victim-') as directory:
            victim = Path(directory) / 'victim'
            victim.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(victim), *args], env=clean, text=True).strip()
            git('init', '-q')
            git('-c', 'user.name=Victim', '-c', 'user.email=victim@example.invalid',
                'commit', '-qm', 'victim', '--allow-empty')
            git('branch', 'preserve-me')
            def snapshot():
                metadata = victim / '.git'
                paths = [metadata / 'config', metadata / 'HEAD', metadata / 'packed-refs',
                         *sorted((metadata / 'refs').rglob('*'))]
                return {str(path.relative_to(metadata)): path.read_bytes() if path.is_file() else None
                        for path in paths}
            before = snapshot()
            poisoned = {**clean, 'GIT_DIR': str(victim / '.git'), 'GIT_WORK_TREE': str(victim),
                        'GIT_INDEX_FILE': str(victim / '.git' / 'index'),
                        'GIT_COMMON_DIR': str(victim / '.git'),
                        'GIT_OBJECT_DIRECTORY': str(victim / '.git' / 'objects'),
                        'GIT_ALTERNATE_OBJECT_DIRECTORIES': str(victim / '.git' / 'objects'),
                        'GIT_CEILING_DIRECTORIES': str(victim.parent), 'GIT_PREFIX': 'victim/'}
            commands = [
                [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_checker_no_write.py'],
                ['bun', 'test', 'tests/omp-extension.test.js'],
            ]
            for command in commands:
                with self.subTest(command=command):
                    result = subprocess.run(command, cwd=ROOT, env=poisoned, capture_output=True,
                                            text=True, timeout=60)
                    self.assertEqual(snapshot(), before, result.stdout + result.stderr)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            fixture = Path(directory) / 'runner-fixture'
            fixture.mkdir()
            command = shlex.join(['git', 'init', '-q']) + '; git config user.name Runner'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'run-check.py'),
                                     '--command', command, '--cwd', str(fixture)],
                                    cwd=ROOT, env=poisoned, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            try:
                self.assertEqual(snapshot(), before)
                self.assertEqual(report['status'], 'passed', report)
                self.assertTrue((fixture / '.git').is_dir())
                self.assertEqual(subprocess.check_output(['git', '-C', str(fixture), 'config', 'user.name'],
                                                        env=clean, text=True).strip(), 'Runner')
            finally:
                Path(report['logPath']).unlink()
            subprocess.run(['git', '-C', str(fixture), '-c', 'user.email=runner@example.invalid',
                            'commit', '-qm', 'runner fixture', '--allow-empty'], env=clean, check=True,
                           capture_output=True)
            revision = subprocess.check_output(['git', '-C', str(fixture), 'rev-parse', 'HEAD'],
                                               env=clean, text=True).strip()
            plan = fixture / 'implementation-plan.md'
            plan.write_text('### T01 — Verify\n- Depends on: none\n- Targets: none\n'
                            '- Change: Verify.\n- Done when: Verified.\n- Verify: true\n')
            commands = [
                ['check-implementation-plans.py', '--protected-diff', str(plan), '--repo', str(fixture),
                 '--base', revision, '--head', revision],
                ['check-doc-status.py', '--frozen-diff', '--repo', str(fixture),
                 '--base', revision, '--head', revision],
            ]
            for script, *args in commands:
                with self.subTest(script=script):
                    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args],
                                            cwd=ROOT, env=poisoned, capture_output=True, text=True, timeout=10)
                    self.assertEqual(snapshot(), before)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
