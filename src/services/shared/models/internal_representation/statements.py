from pydantic import BaseModel, ConfigDict
from typing import TYPE_CHECKING

from .ranks import Rank

if TYPE_CHECKING:
    from .values import Value
    from .qualifiers import Qualifier
    from .references import Reference


class Statement(BaseModel):
    property: str
    value: "Value"
    rank: Rank
    qualifiers: list["Qualifier"]
    references: list["Reference"]
    statement_id: str

    model_config = ConfigDict(frozen=True)
