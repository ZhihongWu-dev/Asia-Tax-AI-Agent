#!/usr/bin/env python
"""Find the clause and the verbatim sentence to cite (采集任务单.md, step 5). Reads clause.csv and doc.csv, so run
database/tools/build.py first.

  python database/tools/find.py <word> [<word> ...] [--jur cn] [--doc cn.law.eit] [--max 20]
      clauses containing the words (case and spacing ignored), those with the most of the words first, then by BM25;
      each with its cite_id and the sentence around the first word it holds; the sentence is copied from the clause, so it
      passes the verbatim check when used as quote. A word that finds nothing is split into its parts and marked relaxed.
  python database/tools/find.py --cite cn.reg.eit#91
      the whole text of one clause
"""
import argparse
import csv
import io
import math
import re
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
csv.field_size_limit(10 ** 9)
ROOT = Path(__file__).resolve().parents[1]
ENC = "utf-8-sig"
BM25_K, BM25_B = 1.5, 0.75
END = re.compile(r"[。；！？]|[.;:](?=\s|$)")          # sentence ends: CJK marks, or . ; : before a space or the end


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding=ENC, newline="") as f:
        return list(csv.DictReader(f))


def flat(text):
    """One line: line breaks become spaces (the verbatim check ignores spacing, so the result still matches)."""
    return re.sub(r"\s+", " ", text).strip()


def sentence(text, word):
    """The sentence of text that contains word (case-insensitive), cut at sentence ends."""
    t = flat(text.replace("\xad", ""))
    m = re.search(r"\s*".join(re.escape(ch) for ch in re.sub(r"\s+", "", word)), t, re.I)   # a line break may split the word
    if not m:
        return t[:300]
    start = 0
    for e in END.finditer(t, 0, m.start()):
        start = e.end()
    e = END.search(t, m.end())
    end = e.end() if e else len(t)
    return t[start:end].strip()


def squash(s):
    return re.sub(r"[\s\xad]+", "", s).lower()


def split_word(word):
    """Smaller words for one that found nothing: the words of a phrase, the two-character pieces of a Chinese, Japanese or Thai term."""
    parts = [p for p in re.split(r"[\s,;/()（）、，]+", word) if p]
    if len(parts) > 1:
        return parts
    if parts and re.fullmatch(r"[\u0E00-\u0E7F\u3040-\u30FF\u3400-\u9FFF]{3,}", parts[0]):
        return [parts[0][i:i + 2] for i in range(len(parts[0]) - 1)]
    return []


def search(clauses, words, body_of=lambda c: squash(c["text"])):
    """-> (hits, relaxed). A hit: {clause, word (the first word it holds), matched (how many of the words)}. No index: a scan
    finds a two-character term exactly, which a tokenizer does not, and the library is small enough."""
    bodies = [(c, body_of(c)) for c in clauses]
    groups, relaxed = [], []
    for w in words:
        if any(squash(w) in b for _, b in bodies):
            groups.append([w])
        else:
            parts = split_word(w)
            groups.append(parts or [w])
            if parts:
                relaxed.append(w)
    keys = {w: squash(w) for g in groups for w in g}
    found, df, total = [], {w: 0 for w in keys}, 0
    for c, b in bodies:
        total += len(b)
        tf = {w: b.count(k) for w, k in keys.items()}
        for w, n in tf.items():
            df[w] += 1 if n else 0
        matched = sum(1 for g in groups if any(tf[w] for w in g))
        if matched:
            found.append((c, b, tf, matched))
    avg = total / max(1, len(bodies))
    hits = []
    for c, b, tf, matched in found:
        score = 0.0
        for w, n in tf.items():
            if n:
                idf = math.log(1 + (len(bodies) - df[w] + 0.5) / (df[w] + 0.5))
                score += idf * n * (BM25_K + 1) / (n + BM25_K * (1 - BM25_B + BM25_B * len(b) / avg))
        hits.append({"clause": c, "word": next(w for g in groups for w in g if tf[w]), "matched": matched, "score": round(score, 3)})
    hits.sort(key=lambda h: (-h["matched"], -h["score"], len(h["clause"]["text"])))
    return hits, relaxed


def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("words", nargs="*")
    ap.add_argument("--jur", default="", help="only documents of this jurisdiction or pair (doc.jur)")
    ap.add_argument("--doc", default="", help="only this document")
    ap.add_argument("--cite", default="", help="print one clause in full")
    ap.add_argument("--max", type=int, default=20)
    ap.add_argument("--root", default="", help="library folder (default: database/)")
    args = ap.parse_args()
    if args.root:
        ROOT = Path(args.root).resolve()
    clauses = read_csv(ROOT / "clause.csv")
    if not clauses:
        print("! clause.csv is empty or missing: run python database/tools/build.py first")
        return 1
    if args.cite:
        c = next((c for c in clauses if c["cite_id"] == args.cite), None)
        if c is None:
            print("! no clause %s" % args.cite)
            return 1
        print("%s  [%s]\n%s" % (c["cite_id"], c["label"], c["text"]))
        return 0
    if not args.words:
        print("! give one or more words, or --cite <cite_id>")
        return 1
    jur_of = {d["id"]: d["jur"] for d in read_csv(ROOT / "doc.csv")}
    scope = [c for c in clauses if (not args.doc or c["doc_id"] == args.doc) and (not args.jur or jur_of.get(c["doc_id"]) == args.jur)]
    hits, relaxed = search(scope, args.words)
    for h in hits[:args.max]:
        print("%s  [%s]  matched %d, score %s" % (h["clause"]["cite_id"], h["clause"]["label"], h["matched"], h["score"]))
        print("    quote: " + sentence(h["clause"]["text"], h["word"]))
    print("(%d clause(s)%s%s)" % (len(hits), ", first %d shown" % args.max if len(hits) > args.max else "", "; split: " + ", ".join(relaxed) if relaxed else ""))
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main())
