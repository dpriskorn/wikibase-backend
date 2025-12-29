from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal


class MusicalNotationValue(BaseModel):
    kind: Literal["musical_notation"] = Field(default="musical_notation", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#MusicalNotation"

    model_config = ConfigDict(frozen=True)
