from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal


class StringValue(BaseModel):
    kind: Literal["string"] = Field(default="string", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#String"

    model_config = ConfigDict(frozen=True)
