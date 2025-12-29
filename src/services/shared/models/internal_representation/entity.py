from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING, Optional, Any

from .entity_types import EntityKind

if TYPE_CHECKING:
    from .statements import Statement


class Entity(BaseModel):
    id: str
    type: EntityKind
    labels: dict[str, str]
    descriptions: dict[str, str]
    aliases: dict[str, list[str]]
    statements: list["Statement"]
    sitelinks: Optional[dict[str, dict[str, Any]]] = None

    model_config = ConfigDict(frozen=True)
