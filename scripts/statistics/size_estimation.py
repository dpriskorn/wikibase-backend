import requests
import statistics
import sys

API = "https://www.wikidata.org/w/api.php"
ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"

HEADERS = {
    "User-Agent": "wikibase-backend-size-estimator/0.1 (https://github.com/dpriskorn/wikibase-backend)"
}

session = requests.Session()
session.headers.update(HEADERS)


def random_qids(n):
    r = session.get(
        API,
        params={
            "action": "query",
            "list": "random",
            "rnnamespace": 0,
            "rnlimit": n,
            "format": "json",
        },
        timeout=10,
    )
    r.raise_for_status()
    return [x["title"] for x in r.json()["query"]["random"]]


qids = random_qids(300)
sizes = []
total = len(qids)

for i, qid in enumerate(qids, start=1):
    print(f"\rFetching {i}/{total} ({qid})", end="", file=sys.stderr)

    r = session.get(ENTITY.format(qid), timeout=10)
    r.raise_for_status()

    entity = r.json()["entities"][qid]
    if entity.get("type") == "redirect":
        continue

    sizes.append(len(r.content))

print("\nDone.")
print(f"sample size (after redirects): {len(sizes)}")
print(f"mean bytes:   {int(statistics.mean(sizes))}")
print(f"median bytes: {int(statistics.median(sizes))}")
print(f"min / max:    {min(sizes)} / {max(sizes)}")
print(f"stdev:        {int(statistics.stdev(sizes))}")
