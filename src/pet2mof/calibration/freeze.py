"""Shared preregistration guard, called before reading holdout inputs."""
import subprocess


SCIENTIFIC_PATHS = ('src', 'scripts', 'configs', 'docs', 'data/processed/c_series',
                    'Makefile', 'pyproject.toml', 'uv.lock')


def require_freeze(root):
    def git(*args):
        return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
    try:
        head, tag = git('rev-parse', 'HEAD'), git('rev-parse', 'prereg-v1^{commit}')
    except subprocess.CalledProcessError:
        raise ValueError('requires exact frozen prereg-v1 HEAD') from None
    if head != tag:
        raise ValueError('requires exact frozen prereg-v1 HEAD')
    try:
        git('diff', '--exit-code', '--quiet', 'HEAD', '--', *SCIENTIFIC_PATHS)
    except subprocess.CalledProcessError:
        raise ValueError('scientific code/configuration/documents changed after freeze') from None
    if git('ls-files', '--others', '--exclude-standard', '--', *SCIENTIFIC_PATHS):
        raise ValueError('untracked scientific code/configuration is not frozen')
    return head
