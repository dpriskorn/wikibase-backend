from pydantic import ConfigDict
from typing_extensions import Literal
from .base import Value


class EntityValue(Value):
    kind: Literal["entity"] = "entity"
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#WikibaseItem"

    model_config = ConfigDict(frozen=True)
