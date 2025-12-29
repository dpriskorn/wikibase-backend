from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal


class TabularDataValue(BaseModel):
    kind: Literal["tabular_data"] = Field(default="tabular_data", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#TabularData"

    model_config = ConfigDict(frozen=True)
