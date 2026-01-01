import csv
import json
from pathlib import Path

from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.ontology.datatypes import property_shape


def load_property_registry(path: Path) -> PropertyRegistry:
    """Load property registry from CSV and JSON files.

    Returns PropertyRegistry with all property shapes including
    normalization predicates for properties that need them.
    """
    shapes = {}

    csv_path = path / "properties.csv"
    datatypes = {}

    if csv_path.exists():
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                datatypes[row["property_id"]] = row["datatype"]

    for file in path.glob("P*.json"):
        data = json.loads(file.read_text())

        pid = data["id"]
        datatype = datatypes.get(pid, "string")
        labels = data.get("labels", {})
        descriptions = data.get("descriptions", {})

        shapes[pid] = property_shape(
            pid, datatype, labels=labels, descriptions=descriptions
        )

    return PropertyRegistry(properties=shapes)
