from datetime import timezone
from typing import Any, Dict
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field

from models.s3_models import (
    S3Config,
    RevisionMetadata,
    RevisionReadResponse,
)


class S3Client(BaseModel):
    config: S3Config
    client: Any = Field(default=None, exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, config: S3Config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )

        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.client.head_bucket(Bucket=self.config.bucket)
        except ClientError as e:
            if (
                e.response["Error"]["Code"] == "404"
                or e.response["Error"]["Code"] == "NoSuchBucket"
            ):
                try:
                    self.client.create_bucket(Bucket=self.config.bucket)
                except ClientError as ce:
                    print(f"Error creating bucket {self.config.bucket}: {ce}")
                    raise
            else:
                print(f"Error checking bucket {self.config.bucket}: {e}")
                raise
        except Exception as e:
            print(
                f"Unexpected error checking/creating bucket {self.config.bucket}: {e}"
            )
            raise

    def write_revision(
        self,
        entity_id: str,
        revision_id: int,
        data: dict,
        publication_state: str = "pending",
    ) -> RevisionMetadata:
        import json

        key = f"{entity_id}/r{revision_id}.json"
        self.client.put_object(
            Bucket=self.config.bucket,
            Key=key,
            Body=json.dumps(data),
            Metadata={"publication_state": publication_state},
        )
        return RevisionMetadata(key=key)

    def read_revision(self, entity_id: str, revision_id: int) -> RevisionReadResponse:
        """Read S3 object and return parsed JSON"""
        import json

        key = f"{entity_id}/r{revision_id}.json"
        response = self.client.get_object(Bucket=self.config.bucket, Key=key)

        parsed_data = json.loads(response["Body"].read().decode("utf-8"))

        return RevisionReadResponse(
            entity_id=entity_id, revision_id=revision_id, data=parsed_data
        )

    def mark_published(
        self, entity_id: str, revision_id: int, publication_state: str
    ) -> None:
        key = f"{entity_id}/r{revision_id}.json"
        self.client.copy_object(
            Bucket=self.config.bucket,
            CopySource={"Bucket": self.config.bucket, "Key": key},
            Key=key,
            Metadata={"publication_state": publication_state},
            MetadataDirective="REPLACE",
        )

    def read_full_revision(self, entity_id: str, revision_id: int) -> Dict[str, Any]:
        """Read S3 object and return parsed full revision JSON"""
        import json

        key = f"{entity_id}/r{revision_id}.json"
        response = self.client.get_object(Bucket=self.config.bucket, Key=key)

        parsed_data = json.loads(response["Body"].read().decode("utf-8"))

        return parsed_data

    def write_entity_revision(
        self,
        entity_id: str,
        revision_id: int,
        entity_type: str,
        data: dict,
        edit_type: str = "",
        created_by: str = "entity-api",
    ) -> int:
        """Write revision as part of redirect operations (no mark_pending/published flow)"""
        import json
        from datetime import datetime

        revision_data = {
            "schema_version": "1.0.0",
            "revision_id": revision_id,
            "created_at": datetime.now(timezone.utc).isoformat() + "Z",
            "created_by": created_by,
            "is_mass_edit": False,
            "edit_type": edit_type,
            "entity_type": entity_type,
            "is_semi_protected": False,
            "is_locked": False,
            "is_archived": False,
            "is_dangling": False,
            "is_mass_edit_protected": False,
            "is_deleted": False,
            "is_redirect": False,
            "entity": data,
        }

        key = f"{entity_id}/r{revision_id}.json"
        self.client.put_object(
            Bucket=self.config.bucket,
            Key=key,
            Body=json.dumps(revision_data),
            Metadata={"publication_state": "published"},
        )
        return revision_id
