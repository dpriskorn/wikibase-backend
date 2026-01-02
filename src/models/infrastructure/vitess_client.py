import json
from typing import Any, Optional

import pymysql
from pydantic import BaseModel, Field

from models.vitess_models import VitessConfig


class VitessClient(BaseModel):
    config: VitessConfig
    connection: Optional[Any] = Field(default=None, exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, config: VitessConfig, **kwargs):
        super().__init__(config=config, **kwargs)
        self.connection = None
        self._create_tables()

    def connect(self):
        if not self.connection:
            self.connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                passwd=self.config.password,
                database=self.config.database,
                autocommit=True,
            )
        return self.connection

    def _create_tables(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_id_mapping (
                entity_id VARCHAR(50) PRIMARY KEY,
                internal_id BIGINT NOT NULL UNIQUE
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_head (
                entity_id BIGINT PRIMARY KEY,
                head_revision_id BIGINT NOT NULL,
                is_semi_protected BOOLEAN DEFAULT FALSE,
                is_locked BOOLEAN DEFAULT FALSE,
                is_archived BOOLEAN DEFAULT FALSE,
                is_dangling BOOLEAN DEFAULT FALSE,
                is_mass_edit_protected BOOLEAN DEFAULT FALSE,
                is_deleted BOOLEAN DEFAULT FALSE,
                is_redirect BOOLEAN DEFAULT FALSE,
                redirects_to BIGINT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_redirects (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                redirect_from_id BIGINT NOT NULL,
                redirect_to_id BIGINT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255) DEFAULT NULL,
                INDEX idx_redirect_from (redirect_from_id),
                INDEX idx_redirect_to (redirect_to_id),
                UNIQUE KEY unique_redirect (redirect_from_id, redirect_to_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_revisions (
                entity_id BIGINT NOT NULL,
                revision_id BIGINT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_mass_edit BOOLEAN DEFAULT FALSE,
                edit_type VARCHAR(100) DEFAULT '',
                PRIMARY KEY (entity_id, revision_id)
            )
        """
        )

        cursor.close()

    def _resolve_id(self, entity_id: str) -> int:
        """Resolve external entity ID to internal ID (private)

        Returns 0 if not found.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT internal_id FROM entity_id_mapping WHERE entity_id = %s",
            (entity_id,),
        )
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else 0

    def entity_exists(self, entity_id: str) -> bool:
        """Check if entity ID exists in mapping"""
        return self._resolve_id(entity_id) != 0

    def get_head(self, entity_id: str) -> int:
        """Get current head revision for entity

        Returns 0 if entity has no revisions (entity_head row doesn't exist or head_revision_id is NULL)
        """
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            return 0
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT head_revision_id FROM entity_head WHERE entity_id = %s",
            (internal_id,),
        )
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else 0

    def write_entity_revision(
        self,
        entity_id: str,
        revision_id: int,
        data: dict,
        is_mass_edit: bool = False,
        edit_type: str = "",
    ) -> None:
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            raise ValueError(f"Entity {entity_id} not found")
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO entity_revisions (entity_id, revision_id, is_mass_edit, edit_type, data) VALUES (%s, %s, %s, %s)",
            (internal_id, revision_id, is_mass_edit, edit_type, json.dumps(data)),
        )
        cursor.close()

    def read_full_revision(self, entity_id: str, revision_id: int) -> dict:
        """Read entity revision data from S3"""
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            raise ValueError(f"Entity {entity_id} not found")
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data FROM entity_revisions WHERE entity_id = %s AND revision_id = %s",
            (internal_id, revision_id),
        )
        result = cursor.fetchone()
        cursor.close()
        return {
            "revision_id": revision_id,
            "data": json.loads(result[0]) if result[0] else None,
        }

    def insert_revision(
        self,
        entity_id: str,
        revision_id: int,
        is_mass_edit: bool = False,
        edit_type: str = "",
    ) -> None:
        """Insert revision metadata (without entity data). Idempotent - skips if already exists."""
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            raise ValueError(f"Entity {entity_id} not found")
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM entity_revisions WHERE entity_id = %s AND revision_id = %s",
            (internal_id, revision_id),
        )
        if cursor.fetchone() is not None:
            cursor.close()
            return

        cursor.execute(
            "INSERT INTO entity_revisions (entity_id, revision_id, is_mass_edit, edit_type) VALUES (%s, %s, %s, %s)",
            (internal_id, revision_id, is_mass_edit, edit_type),
        )
        cursor.close()

    def is_entity_deleted(self, entity_id: str) -> bool:
        """Check if entity is hard-deleted"""
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            return False
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_deleted FROM entity_head WHERE entity_id = %s",
            (internal_id,),
        )
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else False

    def is_entity_locked(self, entity_id: str) -> bool:
        """Check if entity is locked"""
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            return False
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_locked FROM entity_head WHERE entity_id = %s",
            (internal_id,),
        )
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else False

    def is_entity_archived(self, entity_id: str) -> bool:
        """Check if entity is archived"""
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            return False
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_archived FROM entity_head WHERE entity_id = %s",
            (internal_id,),
        )
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else False

    def set_redirect_target(
        self, entity_id: str, redirects_to_entity_id: str | None
    ) -> None:
        """Mark entity as redirect or clear redirect status"""
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            raise ValueError(f"Entity {entity_id} not found")

        redirects_to_internal_id = None
        if redirects_to_entity_id:
            redirects_to_internal_id = self._resolve_id(redirects_to_entity_id)
            if not redirects_to_internal_id:
                raise ValueError(f"Entity {redirects_to_entity_id} not found")

        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE entity_head SET redirects_to = %s WHERE entity_id = %s",
            (redirects_to_internal_id, internal_id),
        )
        cursor.close()

    def create_redirect(
        self,
        redirect_from_entity_id: str,
        redirect_to_entity_id: str,
        created_by: str = "entity-api",
    ) -> None:
        """Create a redirect relationship between entities"""
        redirect_from_internal_id = self._resolve_id(redirect_from_entity_id)
        redirect_to_internal_id = self._resolve_id(redirect_to_entity_id)

        if not redirect_from_internal_id:
            raise ValueError(f"Source entity {redirect_from_entity_id} not found")
        if not redirect_to_internal_id:
            raise ValueError(f"Target entity {redirect_to_entity_id} not found")

        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO entity_redirects
                   (redirect_from_id, redirect_to_id, created_by)
                   VALUES (%s, %s, %s)""",
            (redirect_from_internal_id, redirect_to_internal_id, created_by),
        )
        cursor.close()

    def get_incoming_redirects(self, entity_internal_id: int) -> list[str]:
        """Get all entity IDs that redirect to this entity (for RDF builder)"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT m.entity_id
                   FROM entity_redirects r
                   JOIN entity_id_mapping m ON r.redirect_from_id = m.internal_id
                   WHERE r.redirect_to_id = %s""",
            (entity_internal_id,),
        )
        result = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return result

    def get_redirect_target(self, entity_id: str) -> str | None:
        """Get where this entity redirects to (if any)"""
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            return None
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT m.entity_id
                   FROM entity_head h
                   WHERE h.entity_id = %s AND h.redirects_to IS NOT NULL""",
            (internal_id,),
        )
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else None

    def register_entity(self, entity_id: str) -> None:
        """Register new entity ID mapping (generates internal ID automatically)"""
        from models.infrastructure.ulid_flake import generate_ulid_flake

        internal_id = generate_ulid_flake()
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO entity_id_mapping (entity_id, internal_id) VALUES (%s, %s)",
            (entity_id, internal_id),
        )
        cursor.close()

    def cas_update_head_with_status(
        self,
        entity_id: int,
        expected_head: int | None,
        new_head: int,
        is_semi_protected: bool,
        is_locked: bool,
        is_archived: bool,
        is_dangling: bool,
        is_mass_edit_protected: bool,
        is_deleted: bool,
        is_redirect: bool = False,
    ) -> bool:
        """Compare-and-swap update to entity_head with status flags"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE entity_head
                   SET head_revision_id = %s,
                       is_semi_protected = %s,
                       is_locked = %s,
                       is_archived = %s,
                       is_dangling = %s,
                       is_mass_edit_protected = %s,
                       is_deleted = %s,
                       is_redirect = %s
                   WHERE entity_id = %s AND head_revision_id = %s""",
            (
                new_head,
                is_semi_protected,
                is_locked,
                is_archived,
                is_dangling,
                is_mass_edit_protected,
                is_deleted,
                is_redirect,
                entity_id,
                expected_head,
            ),
        )
        affected_rows = cursor.rowcount
        cursor.close()
        return affected_rows > 0

    def insert_head_with_status(
        self,
        entity_id: int,
        head_revision_id: int,
        is_semi_protected: bool,
        is_locked: bool,
        is_archived: bool,
        is_dangling: bool,
        is_mass_edit_protected: bool,
        is_deleted: bool,
        is_redirect: bool = False,
    ) -> bool:
        """Insert new entity_head row with status flags (for new entities)"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO entity_head
                       (entity_id, head_revision_id, is_semi_protected, is_locked,
                        is_archived, is_dangling, is_mass_edit_protected, is_deleted, is_redirect)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    entity_id,
                    head_revision_id,
                    is_semi_protected,
                    is_locked,
                    is_archived,
                    is_dangling,
                    is_mass_edit_protected,
                    is_deleted,
                    is_redirect,
                ),
            )
            cursor.close()
            return True
        except pymysql.IntegrityError:
            cursor.close()
            return False

    def get_history(self, entity_id: str) -> list[Any]:
        """Get revision history for an entity"""
        from dataclasses import dataclass

        @dataclass
        class RevisionRecord:
            revision_id: int
            created_at: Any

        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            return []

        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT revision_id, created_at FROM entity_revisions WHERE entity_id = %s ORDER BY created_at DESC",
            (internal_id,),
        )
        result = [
            RevisionRecord(
                revision_id=row[0], created_at=row[1].isoformat() if row[1] else None
            )
            for row in cursor.fetchall()
        ]
        cursor.close()
        return result

    def hard_delete_entity(
        self,
        entity_id: str,
        head_revision_id: int,
    ) -> None:
        """Permanently delete entity and mark in database"""
        internal_id = self._resolve_id(entity_id)
        if not internal_id:
            raise ValueError(f"Entity {entity_id} not found")
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE entity_head
                   SET is_deleted = TRUE,
                       head_revision_id = %s
                   WHERE entity_id = %s""",
            (head_revision_id, internal_id),
        )
        cursor.close()

    def list_locked_entities(self, limit: int) -> list[dict]:
        """List locked entities"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT m.entity_id, h.head_revision_id
                   FROM entity_head h
                   JOIN entity_id_mapping m ON h.entity_id = m.internal_id
                   WHERE h.is_locked = TRUE
                   LIMIT %s""",
            (limit,),
        )
        result = [
            {"entity_id": row[0], "head_revision_id": row[1]}
            for row in cursor.fetchall()
        ]
        cursor.close()
        return result

    def list_semi_protected_entities(self, limit: int) -> list[dict]:
        """List semi-protected entities"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT m.entity_id, h.head_revision_id
                   FROM entity_head h
                   JOIN entity_id_mapping m ON h.entity_id = m.internal_id
                   WHERE h.is_semi_protected = TRUE
                   LIMIT %s""",
            (limit,),
        )
        result = [
            {"entity_id": row[0], "head_revision_id": row[1]}
            for row in cursor.fetchall()
        ]
        cursor.close()
        return result

    def list_archived_entities(self, limit: int) -> list[dict]:
        """List archived entities"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT m.entity_id, h.head_revision_id
                   FROM entity_head h
                   JOIN entity_id_mapping m ON h.entity_id = m.internal_id
                   WHERE h.is_archived = TRUE
                   LIMIT %s""",
            (limit,),
        )
        result = [
            {"entity_id": row[0], "head_revision_id": row[1]}
            for row in cursor.fetchall()
        ]
        cursor.close()
        return result

    def list_dangling_entities(self, limit: int) -> list[dict]:
        """List dangling entities"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT m.entity_id, h.head_revision_id
                   FROM entity_head h
                   JOIN entity_id_mapping m ON h.entity_id = m.internal_id
                   WHERE h.is_dangling = TRUE
                   LIMIT %s""",
            (limit,),
        )
        result = [
            {"entity_id": row[0], "head_revision_id": row[1]}
            for row in cursor.fetchall()
        ]
        cursor.close()
        return result

    def list_by_edit_type(self, edit_type: str, limit: int) -> list[dict]:
        """List entities by edit type"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT DISTINCT m.entity_id, r.edit_type, r.revision_id
                   FROM entity_revisions r
                   JOIN entity_head h ON r.entity_id = h.entity_id
                   JOIN entity_id_mapping m ON h.entity_id = m.internal_id
                   WHERE r.edit_type = %s
                   LIMIT %s""",
            (edit_type, limit),
        )
        result = [
            {"entity_id": row[0], "edit_type": row[1], "revision_id": row[2]}
            for row in cursor.fetchall()
        ]
        cursor.close()
        return result
