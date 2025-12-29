from pydantic import ConfigDict, Field
from typing_extensions import Literal
from .base import Value


class SomeValue(Value):
    kind: Literal["somevalue"] = Field(default="somevalue", frozen=True)
    value: None = None
    datatype_uri: str = "http://wikiba.se/ontology#SomeValue"

    model_config = ConfigDict(frozen=True)
