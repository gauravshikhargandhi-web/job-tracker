"""One-off check of what each careers site answers, run on GitHub (the sites block the build machine).

    python tools/probe.py tools/probe_urls.txt probe_out

Saves each answer's status, final address, headers and the first 60,000 characters.
"""

import json
import os
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def main(listing, out):
    os.makedirs(out, exist_ok=True)
    results = []
    for n, line in enumerate(l.strip() for l in open(listing)):
        if not line or line.startswith("#"):
            continue
        name, url = line.split(" ", 1)
        body = None
        if url.startswith("POST "):
            url, body = url[5:].split(" ", 1)
        req = urllib.request.Request(url, data=body.encode() if body else None,
                                     headers={"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*",
                                              "Content-Type": "application/json"})
        row = {"name": name, "url": url}
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                text = r.read().decode("utf-8", "replace")
                row.update(status=r.status, final=r.geturl(), type=r.headers.get("Content-Type", ""))
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            row.update(status=e.code, final=url)
        except Exception as e:
            text = ""
            row.update(status=str(e))
        row["length"] = len(text)
        path = f"{out}/{n:02d}-{name}.txt"
        open(path, "w").write(text[:60000])
        row["file"] = path
        results.append(row)
        print(row)
    json.dump(results, open(f"{out}/results.json", "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
