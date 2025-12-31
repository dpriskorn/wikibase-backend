from models.internal_representation.statements import Statement as InternalStatement

class RDFStatement:
    """
    RDF statement model for Turtle generation.
    Concern: Generate statement URI from GUID.
    
    Wikidata uses wds: prefix with GUID (not hash).
    
    Transformation: Replace '$' with '-' in GUID for URI-safe format.
    
    Examples:
      - JSON: "Q17948861$FA20AC3A-5627-4EC5-93CA-24F0F00C8AA6"
      - RDF:  "Q17948861-FA20AC3A-5627-4EC5-93CA-24F0F00C8AA6"
    """
    
    def __init__(self, statement: InternalStatement):
        self.guid = statement.statement_id
        self.property_id = statement.property
        self.value = statement.value
        self.rank = statement.rank.value
        self.qualifiers = statement.qualifiers
        self.references = statement.references
