from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal


class EntitySchemaValue(BaseModel):
    kind: Literal["entity_schema"] = Field(default="entity_schema", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#EntitySchema"

    model_config = ConfigDict(frozen=True)
