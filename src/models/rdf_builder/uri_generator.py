from pydantic import BaseModel, ConfigDict


class URIGenerator(BaseModel):
    wd: str = "http://www.wikidata.org/entity"
    data: str = "https://www.wikidata.org/wiki/Special:EntityData"
    wds: str = "http://www.wikidata.org/entity/statement"

    model_config = ConfigDict(frozen=True)

    def entity_uri(self, entity_id: str) -> str:
        return f"{self.wd}/{entity_id}"

    def data_uri(self, entity_id: str) -> str:
        return f"{self.data}/{entity_id}"

    def statement_uri(self, statement_id: str) -> str:
        statement_id_normalized = statement_id.replace('$', '-')
        return f"{self.wds}/{statement_id_normalized}"

    def entity_prefixed(self, entity_id: str) -> str:
        return f"wd:{entity_id}"

    def data_prefixed(self, entity_id: str) -> str:
        return f"data:{entity_id}"

    def statement_prefixed(self, statement_id: str) -> str:
        statement_id_normalized = statement_id.replace('$', '-')
        return f"wds:{statement_id_normalized}"
