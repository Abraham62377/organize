import pytest
from mock import patch
from organize.utils import Path


@pytest.fixture
def mock_exists():
    with patch.object(Path, 'exists') as mck:
        yield mck


@pytest.fixture
def mock_move():
    with patch('shutil.move') as mck:
        yield mck


@pytest.fixture
def mock_remove():
    with patch('os.remove') as mck:
        yield mck


@pytest.fixture
def mock_parent():
    with patch.object(Path, 'parent') as mck:
        yield mck


@pytest.fixture
def mock_mkdir():
    with patch.object(Path, 'mkdir') as mck:
        yield mck
