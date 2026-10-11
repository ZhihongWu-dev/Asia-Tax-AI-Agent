import io
import sys

from ..params import Params
from .compile import compile_rules, dump
from .spec import SPEC

out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
orphans = []
rules = compile_rules(SPEC, Params(), report=orphans)
dump(rules, out)
out.write("%d rules; orphan rate/condition parameters in scope: %d\n" % (len(rules), len(orphans)))
for pid in orphans:
    out.write("  - %s\n" % pid)
out.flush()
