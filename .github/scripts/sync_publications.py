#!/usr/bin/env python3
"""Regenerate _data/publist.yml from https://machiry.github.io/publications/.

The source page is the single source of truth: every <p> entry inside its
<div class="cv"> becomes one publication here, in the same order. PDFs under
/files/ that are missing locally are downloaded from the source site.
"""
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

SOURCE_SITE = "https://machiry.github.io"
SOURCE_PAGE = SOURCE_SITE + "/publications/"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PUBLIST = os.path.join(REPO_ROOT, "_data", "publist.yml")
# Refuse to overwrite the list if the source suddenly looks very different.
MIN_ENTRIES = 30


class PublicationParser(HTMLParser):
    """Collects each entry as a list of <br>-separated segments."""

    def __init__(self):
        super().__init__()
        self.div_depth = 0  # depth inside <div class="cv">, 0 = outside
        self.entry = None
        self.entries = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            if self.div_depth:
                self.div_depth += 1
            elif "cv" in (attrs.get("class") or "").split():
                self.div_depth = 1
        if not self.div_depth:
            return
        if tag == "p":
            self.finish_entry()
            self.entry = [{"text": "", "links": [], "strong": False}]
        elif tag == "strong" and self.entry is None:
            # Some source entries are missing their opening <p>.
            self.entry = [{"text": "", "links": [], "strong": True}]
        elif self.entry is None:
            return
        elif tag == "br":
            self.entry.append({"text": "", "links": [], "strong": False})
        elif tag == "a" and attrs.get("href"):
            self.entry[-1]["links"].append(attrs["href"])
        elif tag == "strong":
            self.entry[-1]["strong"] = True

    def handle_endtag(self, tag):
        if tag == "div" and self.div_depth:
            self.div_depth -= 1
            if not self.div_depth:
                self.finish_entry()
        elif tag == "p":
            self.finish_entry()

    def finish_entry(self):
        if self.entry is not None:
            self.entries.append(self.entry)
            self.entry = None

    def handle_data(self, data):
        if self.entry is not None:
            self.entry[-1]["text"] += data


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def to_publication(segments):
    segs = [s for s in segments if clean(s["text"]) or s["links"]]
    if len(segs) < 3 or not segs[0]["strong"]:
        return None
    title = re.sub(r"\s*:\s*", " - ", clean(segs[0]["text"]), count=1)
    if not title.endswith((".", "?", ")")):
        title += "."
    authors = clean(segs[1]["text"])
    authors = re.sub(r"\s+,", ",", authors).rstrip(" .")
    venue, _, rest = clean(segs[2]["text"]).partition(":")
    display = clean(venue)
    if rest.strip():
        display += " - " + rest.strip()
    url = ""
    for seg in segs[3:]:
        if seg["links"] and not seg["strong"]:  # skip award links
            url = seg["links"][0]
            break
    return {"title": title, "authors": authors, "url": url, "display": display}


def yaml_scalar(value):
    if value == "":
        return ""
    if (": " in value or " #" in value or value.endswith(":")
            or value[0] in "!&*[]{}|>'\"%@`#,?-"):
        return json.dumps(value, ensure_ascii=False)
    return value


def render(pubs):
    out = []
    for p in pubs:
        out.append(
            f"- title: {yaml_scalar(p['title'])}\n"
            f"  authors: {yaml_scalar(p['authors'])}\n"
            f"  description:\n"
            f"  link:\n"
            f"    url: {yaml_scalar(p['url'])}\n"
            f"    display: {yaml_scalar(p['display'])}\n"
            f"  highlight: 0\n"
            f"  news2:\n"
        )
    return re.sub(r" +\n", "\n", "\n".join(out))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "purs3lab-sync"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def download_missing_files(pubs):
    for p in pubs:
        url = p["url"]
        if not url.startswith("/files/"):
            continue
        local = os.path.join(REPO_ROOT, url.lstrip("/"))
        if os.path.exists(local):
            continue
        try:
            data = fetch(SOURCE_SITE + url)
        except Exception as e:  # keep the entry; the link just won't resolve yet
            print(f"warning: could not download {url}: {e}", file=sys.stderr)
            continue
        with open(local, "wb") as f:
            f.write(data)
        print(f"downloaded {url}")


def main():
    parser = PublicationParser()
    parser.feed(fetch(SOURCE_PAGE).decode("utf-8"))
    pubs = [p for p in map(to_publication, parser.entries) if p]
    if len(pubs) < MIN_ENTRIES:
        sys.exit(f"error: only {len(pubs)} publications parsed; not updating")
    download_missing_files(pubs)
    with open(PUBLIST, "w", encoding="utf-8") as f:
        f.write(render(pubs))
    print(f"wrote {len(pubs)} publications")


if __name__ == "__main__":
    main()
