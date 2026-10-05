"""Keep inherited Git hook state out of explicitly selected repositories."""
import os
import sys


def clean_git_environment():
    """Preserve ordinary command settings, but discard all inherited GIT_* overrides."""
    return {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('usage: git_environment.py COMMAND [ARG ...]')
    os.execvpe(sys.argv[1], sys.argv[1:], clean_git_environment())
