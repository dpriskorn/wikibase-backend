import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture(scope="session", autouse=True)
def skip_api_waiter():
    """Override the API wait fixture from parent conftest"""
    pass
