"""Audit main-only citations against immutable archives and the rebuilt library.

Exact textual containment is structural evidence, never legal equivalence or
permission to publish a candidate. No source/review status is modified.
"""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile


def blob_id(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def table(data, key):
    csv.field_size_limit(10**9)
    rows = list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate table identifiers')
    return result


def verified_table(archive, ref, path, key):
    tree = subprocess.run(['git','ls-tree',ref,'--',path],
        env={**os.environ,'GIT_NO_LAZY_FETCH':'1'}, capture_output=True,
        text=True, check=True, timeout=15).stdout.strip()
    expected = tree.split()[2]
    matches = [n for n in archive.namelist() if n.endswith('/'+path)]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous archive entry: '+path)
    data = archive.read(matches[0])
    if blob_id(data) != expected:
        raise ValueError('Archive does not match pinned Git tree: '+path)
    return table(data,key), expected


def normalized(text):
    return re.sub(r'\s+','',text)


def audit(main, li, main_docs, current_docs, root, archive):
    output=[]
    root=root.resolve()
    for cite in sorted(main.keys()-li.keys()):
        clause=main[cite]; doc=main_docs[clause['doc_id']]
        current=current_docs.get(clause['doc_id'])
        original_entries=[n for n in archive.namelist() if n.endswith('/database/'+doc['file'])]
        original_verified=(len(original_entries)==1 and hashlib.sha256(
            archive.read(original_entries[0])).hexdigest()==doc['sha256'])
        current_verified=False
        if current:
            path=(root/current['file']).resolve()
            if path.is_relative_to(root) and path.is_file():
                current_verified=hashlib.sha256(path.read_bytes()).hexdigest()==current['sha256']
        # Registry IDs determine filenames but must never escape the text root.
        text_path=(root/'text'/(clause['doc_id']+'.txt')).resolve()
        text=text_path.read_text(encoding='utf-8-sig') if text_path.is_relative_to(root/'text') and text_path.is_file() else ''
        old_text=normalized(clause['text'])
        contained=bool(old_text) and old_text in normalized(text)
        source_same=bool(current and current['sha256']==doc['sha256'])
        classification=('exact_text_same_source' if contained and source_same and current_verified and original_verified
            else 'text_or_source_review_required')
        output.append(dict(cite_id=cite,doc_id=doc['id'],classification=classification,
            main_text_sha256=hashlib.sha256(clause['text'].encode()).hexdigest(),
            main_source_sha256=doc['sha256'],main_original_verified=original_verified,
            current_source_sha256=current['sha256'] if current else None,
            current_original_verified=current_verified,source_bytes_unchanged=source_same,
            entire_main_text_contained_ignoring_whitespace=contained,
            main_text_characters=len(clause['text']),current_text_characters=len(text),
            publication_status='candidate_not_approved'))
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-archive',type=Path,required=True)
    parser.add_argument('--li-archive',type=Path,required=True)
    parser.add_argument('--main-ref',required=True)
    parser.add_argument('--li-ref',required=True)
    parser.add_argument('--root',type=Path,default=Path('database'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--bundle',type=Path,help='Preserve candidate texts; does not approve publication')
    args=parser.parse_args()
    with zipfile.ZipFile(args.main_archive) as old, zipfile.ZipFile(args.li_archive) as new:
        main_rows,main_blob=verified_table(old,args.main_ref,'database/clause.csv','cite_id')
        li_rows,li_blob=verified_table(new,args.li_ref,'database/clause.csv','cite_id')
        docs,doc_blob=verified_table(old,args.main_ref,'database/doc.csv','id')
        current=table((args.root/'doc.csv').read_bytes(),'id')
        rows=audit(main_rows,li_rows,docs,current,args.root,old)
    report=dict(main_ref=args.main_ref,li_ref=args.li_ref,
        verified_blobs=dict(main_clauses=main_blob,main_docs=doc_blob,li_clauses=li_blob),
        counts=dict(main_clauses=len(main_rows),li_clauses=len(li_rows),main_only=len(rows),
                    classifications=dict(Counter(r['classification'] for r in rows))),
        legal_review='not_established_by_text_containment',citations=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.bundle:
        if not all(row['main_original_verified'] for row in rows):
            raise ValueError('Cannot bundle unverified originals')
        bundle=dict(format_version=1,source_commit=args.main_ref,verified_blobs=report['verified_blobs'],
            publication_status='candidate_not_approved',
            records=[dict(cite_id=row['cite_id'],clause=main_rows[row['cite_id']],
                          document=docs[row['doc_id']],text_sha256=row['main_text_sha256']) for row in rows])
        args.bundle.parent.mkdir(parents=True,exist_ok=True)
        args.bundle.write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['counts']))


if __name__=='__main__':
    main()
