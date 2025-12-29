from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import Literal


class MonolingualValue(BaseModel):
    kind: Literal["monolingual"] = Field(default="monolingual", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#MonolingualText"
    language: str
    text: str

    model_config = ConfigDict(frozen=True)

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if "\n" in v or "\r" in v:
            raise ValueError("MonolingualText text must not contain newline characters")
        return v
