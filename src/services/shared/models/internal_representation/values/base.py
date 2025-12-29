from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Value(BaseModel):
    kind: Literal[
        "entity",
        "string",
        "time",
        "quantity",
        "globe",
        "monolingual",
        "external_id",
        "commons_media",
        "geo_shape",
        "tabular_data",
        "musical_notation",
        "url",
        "math",
        "entity_schema"
    ]
    value: Any
    datatype_uri: str

    model_config = ConfigDict(frozen=True)
