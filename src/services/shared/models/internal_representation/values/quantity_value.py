from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Literal
from typing import Optional


class QuantityValue(BaseModel):
    kind: Literal["quantity"] = Field(default="quantity", frozen=True)
    value: str
    datatype_uri: str = "http://wikiba.se/ontology#Quantity"
    unit: str = "1"
    upper_bound: Optional[str] = None
    lower_bound: Optional[str] = None

    model_config = ConfigDict(frozen=True)

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if v.startswith("Q"):
            v = "http://www.wikidata.org/entity/" + v
        return v

    @field_validator("value", "upper_bound", "lower_bound")
    @classmethod
    def validate_numeric(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                float(v)
            except ValueError:
                raise ValueError(f"Value must be a valid number, got: {v}")
        return v

    @model_validator(mode="after")
    def validate_bounds(self) -> "QuantityValue":
        amount = float(self.value)
        upper = float(self.upper_bound) if self.upper_bound else None
        lower = float(self.lower_bound) if self.lower_bound else None

        if lower is not None and upper is not None:
            if lower > upper:
                raise ValueError("Lower bound cannot be greater than upper bound")
            if lower > amount:
                raise ValueError("Lower bound cannot be greater than amount")
        if upper is not None and upper < amount:
            raise ValueError("Upper bound cannot be less than amount")
        return self
