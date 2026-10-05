"""Sanitize the suite before any fixture can launch Git, including via child CLIs."""
import os
from pathlib import Path
import sys

# Make sibling script imports work for both CLI tests and importlib-loaded scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from git_environment import clean_git_environment

for key in set(os.environ) - set(clean_git_environment()):
    del os.environ[key]
