from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal


class EntityValue(BaseModel):
    kind: Literal["entity"] = Field(default="entity", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#WikibaseItem"

    model_config = ConfigDict(frozen=True)
