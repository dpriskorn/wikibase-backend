import time
import logging
import os
from typing import Generator

import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for all test sessions"""
    log_level_str = os.getenv("TEST_LOG_LEVEL", "INFO")
    log_level = logging.DEBUG if log_level_str == 'DEBUG' else logging.INFO

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        force=True
    )


@pytest.fixture(scope="session")
def base_url() -> str:
    """API base URL from environment or default"""
    return os.getenv("ENTITY_API_URL", "http://entity-api:8000")


@pytest.fixture(scope="session")
def api_client(base_url: str) -> Generator[requests.Session, None, None]:
    """Requests session for making HTTP calls"""
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture(scope="session", autouse=True)
def wait_for_api(api_client: requests.Session, base_url: str) -> None:
    """Wait for API to become healthy before running tests"""
    max_retries = 30
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = api_client.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    logging.info(f"API healthy after {attempt + 1} attempts")
                    return
        except requests.RequestException:
            pass
        time.sleep(retry_delay)
    
    raise Exception("API did not become healthy within timeout")


def log_request(logger: logging.Logger, method: str, url: str, **kwargs) -> requests.Response:
    """Log HTTP request and make the request"""
    if os.getenv("TEST_LOG_HTTP_REQUESTS") == "true":
        if 'json' in kwargs:
            body_preview = str(kwargs['json'])[:200]
            logger.debug(f"  → {method} {url}")
            logger.debug(f"    Body: {body_preview}...")
        else:
            logger.debug(f"  → {method} {url}")
    
    return requests.request(method, url, **kwargs)


def log_response(logger: logging.Logger, response: requests.Response, log_body: bool = False) -> None:
    """Log HTTP response with status code and optional body
    
    Args:
        logger: Logger instance
        response: requests.Response object
        log_body: If True, log response body text (default: False)
    """
    if os.getenv("TEST_LOG_HTTP_REQUESTS") == "true":
        status_code = response.status_code
        status_emoji = "✓" if status_code < 300 else "✗"
        logger.debug(f"  ← {status_emoji} {status_code} {response.reason}")
        if log_body and response.text:
            text_preview = response.text[:200]
            logger.debug(f"    Body: {text_preview}...")
