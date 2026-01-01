from models.internal_representation.references import Reference


class RDFReference:
    """
    RDF reference model for Turtle generation.
    Concern: Generate reference URI from hash (stored in IR).

    Wikidata uses wdref: prefix with SHA1 hash.
    Example: http://www.wikidata.org/reference/a4d108601216cffd2ff1819ccf12b483486b62e7
    """

    def __init__(self, reference: Reference, statement_uri: str):
        self.statement_uri = statement_uri

        if not reference.hash:
            raise ValueError(
                f"Reference has no hash. "
                f"Cannot generate wdref: URI for statement: {statement_uri}"
            )
        self.hash = reference.hash

    def get_reference_uri(self) -> str:
        """Generate wdref: URI from hash."""
        return f"wdref:{self.hash}"
