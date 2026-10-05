"""All checker modes preserve project files and stale Git metadata."""
import git_test_environment  # Scrub inherited Git hook state before fixture creation.
import os
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CheckerNoWriteTests(unittest.TestCase):
    def test_every_mode_preserves_stale_index_refs_and_worktrees(self):
        with tempfile.TemporaryDirectory(prefix='playbook-readonly-') as directory:
            repo = Path(directory) / 'repo'
            repo.mkdir()

            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()

            git('init', '-q')
            git('config', 'user.name', 'Fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            (repo / '.gitignore').write_text('.worktrees/\n')
            (repo / 'tracked.txt').write_text('unchanged\n')
            docs = repo / 'docs'
            docs.mkdir()
            doc = docs / 'product-vision.md'
            body = b'# Vision\n'
            doc.write_bytes(b'---\nstate: active\nrevision: vision-r1\n---\n' + body)
            (docs / 'user-approvals.json').write_text(json.dumps({
                'docs/product-vision.md': hashlib.sha256(body).hexdigest(),
            }))
            worktree = repo / '.worktrees' / 'T01'
            plan = repo / 'implementation-plan.md'
            plan.write_text('### T01 — Verify\n- Depends on: none\n- Targets: none\n'
                            '- Change: Verify behavior.\n- Done when: Verified.\n- Verify: true\n'
                            f'- Assigned worktree: {worktree}\n- Assigned branch: impl/T01\n')
            git('add', '.')
            git('commit', '-qm', 'fixture')
            base = git('rev-parse', 'HEAD')
            git('worktree', 'add', '-qb', 'impl/T01', str(worktree), base)
            # Preserve content but invalidate index stat caches in both checkouts.
            for path in [repo / 'tracked.txt', worktree / 'tracked.txt']:
                stamp = path.stat().st_mtime_ns
                os.utime(path, ns=(stamp + 2_000_000_000, stamp + 2_000_000_000))

            def snapshot():
                return {str(path.relative_to(repo)): (
                            path.read_bytes() if path.is_file() else None, path.stat().st_mtime_ns)
                        for path in [repo, *repo.rglob('*')]}

            before = snapshot()
            refs = git('show-ref')
            metadata = git('worktree', 'list', '--porcelain')
            commands = [
                ['check-implementation-plans.py', '--check', str(plan)],
                ['check-implementation-plans.py', '--json', str(plan)],
                ['check-implementation-plans.py', '--protected-diff', str(plan), '--repo', str(repo),
                 '--base', base, '--head', base, '--task', 'T01', '--worktree-root', str(repo / '.worktrees')],
                ['check-doc-status.py', '--check', str(doc)],
                ['check-doc-status.py', '--json', str(doc)],
                ['check-doc-status.py', '--frozen-diff', '--repo', str(repo), '--base', base, '--head', base],
            ]
            for script, *args in commands:
                with self.subTest(script=script, args=args):
                    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *args],
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(snapshot(), before)
                    self.assertEqual(git('show-ref'), refs)
                    self.assertEqual(git('worktree', 'list', '--porcelain'), metadata)
            # Prove this fixture would expose an accidental refreshing status.
            index = repo / '.git' / 'worktrees' / 'T01' / 'index'
            index_before = (index.read_bytes(), index.stat().st_mtime_ns)
            subprocess.run(['git', '-C', str(worktree), 'status', '--porcelain'], check=True, capture_output=True)
            self.assertNotEqual((index.read_bytes(), index.stat().st_mtime_ns), index_before)
