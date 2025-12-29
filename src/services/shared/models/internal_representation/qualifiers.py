from pydantic import BaseModel, ConfigDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .values import Value


class Qualifier(BaseModel):
    property: str
    value: "Value"

    model_config = ConfigDict(frozen=True)
