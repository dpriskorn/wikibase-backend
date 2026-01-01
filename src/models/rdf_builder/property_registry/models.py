from pydantic import BaseModel, ConfigDict


class PropertyPredicates(BaseModel):
    direct: str
    statement: str
    qualifier: str
    reference: str
    value_node: str | None = None
    qualifier_value: str | None = None
    reference_value: str | None = None
    statement_normalized: str | None = None
    qualifier_normalized: str | None = None
    reference_normalized: str | None = None
    direct_normalized: str | None = None

    model_config = ConfigDict(frozen=True)


def get_owl_type(datatype: str) -> str:
    """Map datatype to OWL property type.

    Returns 'owl:DatatypeProperty' for non-item datatypes,
    'owl:ObjectProperty' for item-type properties.
    """
    object_properties = {
        "wikibase-item",
        "wikibase-lexeme",
        "wikibase-form",
        "wikibase-sense",
        "wikibase-property",
        "commonsmedia",
        "commonsMedia",
        "string",
        "url",
        "math",
        "geo-shape",
        "monolingualtext",
        "external-id",
        "tabular-data",
        "musical-notation",
        "entity-schema",
    }
    return (
        "owl:ObjectProperty"
        if datatype in object_properties
        else "owl:DatatypeProperty"
    )


class PropertyShape(BaseModel):
    pid: str
    datatype: str
    predicates: PropertyPredicates
    labels: dict[str, dict] = {}
    descriptions: dict[str, dict] = {}

    model_config = ConfigDict(frozen=True)
