from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal


class URLValue(BaseModel):
    kind: Literal["url"] = Field(default="url", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#Url"

    model_config = ConfigDict(frozen=True)
