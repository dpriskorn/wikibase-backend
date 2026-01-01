import requests
import statistics
import sys
import time

API = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "wikibase-backend-revision-estimator/0.1 (https://github.com/dpriskorn/wikibase-backend)"
}

session = requests.Session()
session.headers.update(HEADERS)


def random_qids(n, batch=50):
    qids = []
    while len(qids) < n:
        r = session.get(
            API,
            params={
                "action": "query",
                "list": "random",
                "rnnamespace": 0,
                "rnlimit": min(batch, n - len(qids)),
                "format": "json",
            },
            timeout=10,
        )
        r.raise_for_status()
        qids.extend(x["title"] for x in r.json()["query"]["random"])
    return qids


def count_revisions(qid):
    count = 0
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": qid,
        "rvlimit": "max",
        "rvprop": "ids",
        "format": "json",
    }

    while True:
        r = session.get(API, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        page = next(iter(data["query"]["pages"].values()))
        revs = page.get("revisions", [])
        count += len(revs)

        if "continue" not in data:
            break

        params.update(data["continue"])

        # be polite
        time.sleep(0.05)

    return count


qids = random_qids(300)
rev_counts = []
total = len(qids)

for i, qid in enumerate(qids, start=1):
    print(f"\rCounting revisions {i}/{total} ({qid})", end="", file=sys.stderr)

    revs = count_revisions(qid)
    if revs == 0:
        continue  # extremely rare, but safe

    rev_counts.append(revs)

print("\nDone.")
print(f"sample size: {len(rev_counts)}")
print(f"mean revisions:   {int(statistics.mean(rev_counts))}")
print(f"median revisions: {int(statistics.median(rev_counts))}")
print(f"min / max:        {min(rev_counts)} / {max(rev_counts)}")
print(f"stdev:            {int(statistics.stdev(rev_counts))}")
