import logging
from pydantic_settings import BaseSettings
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from infrastructure.s3_client import S3Config
    from infrastructure.vitess_client import VitessConfig


class Settings(BaseSettings):
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    vitess_host: str
    vitess_port: int
    vitess_database: str = "wikibase"
    vitess_user: str = "root"
    vitess_password: str = ""
    test_log_level: str = "INFO"
    test_log_http_requests: bool = False
    test_show_progress: bool = True

    class Config:
        env_file = ".env"
    
    def to_s3_config(self):
        from infrastructure.s3_client import S3Config
        return S3Config(
            endpoint_url=self.s3_endpoint,
            access_key=self.s3_access_key,
            secret_key=self.s3_secret_key,
            bucket=self.s3_bucket
        )
    
    def to_vitess_config(self):
        from infrastructure.vitess_client import VitessConfig
        return VitessConfig(
            host=self.vitess_host,
            port=self.vitess_port,
            database=self.vitess_database,
            user=self.vitess_user,
            password=self.vitess_password
        )


# noinspection PyArgumentList
settings = Settings()

logger.debug("=== Settings Debug ===")
logger.debug(f"S3 Endpoint: {settings.s3_endpoint}")
logger.debug(f"S3 Bucket: {settings.s3_bucket}")
logger.debug(f"Vitess Host: {settings.vitess_host}")
logger.debug(f"Vitess Port: {settings.vitess_port}")
logger.debug(f"Vitess Database: {settings.vitess_database}")
logger.debug(f"Test Log Level: {settings.test_log_level}")
logger.debug(f"Test Log HTTP Requests: {settings.test_log_http_requests}")
logger.debug(f"Test Show Progress: {settings.test_show_progress}")
logger.debug("=== End Settings Debug ===")
logger.debug(f"Test Log Level: {settings.test_log_level}")
logger.debug(f"Test Log HTTP Requests: {settings.test_log_http_requests}")
logger.debug(f"Test Show Progress: {settings.test_show_progress}")
