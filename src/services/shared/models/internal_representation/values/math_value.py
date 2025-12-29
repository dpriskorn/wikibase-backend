from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal


class MathValue(BaseModel):
    kind: Literal["math"] = Field(default="math", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#Math"

    model_config = ConfigDict(frozen=True)
