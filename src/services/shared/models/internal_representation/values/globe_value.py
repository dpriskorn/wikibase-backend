from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import Literal
from typing import Optional


class GlobeValue(BaseModel):
    kind: Literal["globe"] = Field(default="globe", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#GlobeCoordinate"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude: Optional[float] = None
    precision: float = 1 / 3600
    globe: str = "http://www.wikidata.org/entity/Q2"

    model_config = ConfigDict(frozen=True)

    @field_validator("globe")
    @classmethod
    def validate_globe(cls, v: str) -> str:
        if v.startswith("Q"):
            v = "http://www.wikidata.org/entity/" + v
        return v
