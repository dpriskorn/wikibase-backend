import logging

import pytest
import sys
from pathlib import Path

# sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
TEST_DATA_JSON_DIR = Path(__file__).parent.parent.parent / "test_data" / "json"
logger = logging.getLogger(__name__)
# logger.info(f"TEST_DATA_DIR: {TEST_DATA_JSON_DIR}")
# print(f"TEST_DATA_DIR: {TEST_DATA_JSON_DIR}")

@pytest.fixture(scope="session", autouse=True)
def skip_api_waiter():
    """Override the API wait fixture from parent conftest"""
    pass
