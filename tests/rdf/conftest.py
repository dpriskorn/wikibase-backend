from pathlib import Path
import re

# Resolve project root:
# tests/rdf/conftest.py → tests/rdf → tests → project root
# PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEST_DATA_JSON_DIR = Path(__file__).parent.parent.parent / "test_data" / "json"

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def normalize_ttl(ttl: str) -> str:
    ttl = re.sub(r"#.*$", "", ttl, flags=re.MULTILINE)
    ttl = re.sub(r"[ \t]+", " ", ttl)
    ttl = re.sub(r"\n{3,}", "\n\n", ttl)
    return ttl.strip()

def split_subject_blocks(ttl: str) -> dict[str, str]:
    blocks = {}
    current_subject = None
    current_lines = []

    for line in ttl.splitlines():
        if line and not line.startswith((" ", "\t")):
            if current_subject:
                blocks[current_subject] = "\n".join(current_lines).strip()
            current_subject = line.split()[0]
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_subject:
        blocks[current_subject] = "\n".join(current_lines).strip()

    return blocks
