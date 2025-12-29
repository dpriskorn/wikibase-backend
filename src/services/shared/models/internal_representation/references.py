from pydantic import BaseModel, ConfigDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .values import Value


class ReferenceValue(BaseModel):
    property: str
    value: "Value"

    model_config = ConfigDict(frozen=True)


class Reference(BaseModel):
    hash: str
    snaks: list[ReferenceValue]

    model_config = ConfigDict(frozen=True)
