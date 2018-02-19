from unittest.mock import patch

from organize.actions import Shell
from organize.utils import Path


def test_shell_basic():
    with patch('subprocess.run') as m:
        shell = Shell("echo 'Hello World'")
        shell.run(Path('~'), {}, False)
        m.assert_called_with("echo 'Hello World'", shell=True)


def test_shell_attrs():
    with patch('subprocess.run') as m:
        shell = Shell('echo {year}')
        shell.run(Path('~'), {'year': 2017}, False)
        m.assert_called_with('echo 2017', shell=True)


def test_shell_path():
    with patch('subprocess.run') as m:
        shell = Shell('echo {path.stem} for {year}')
        shell.run(Path('/this/isafile.txt'), {'year': 2017}, False)
        m.assert_called_with('echo isafile for 2017', shell=True)
