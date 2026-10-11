"""Coverage matrix (场景.md §3): jurisdiction x side x income -> CHARGE rules, an explicit NOCHARGE, or MISSING.

  python -m tax_graph.check_coverage          (conda env "pytorch")

MISSING cells are reported, not failed: they are the work list. The closed-world assumption "no rule = no tax" is
only acceptable where a NOCHARGE declaration with a cite stands in the cell.
"""
import io
import sys

from .flow_tax import RULES
from .rules.compile import INCOMES, JURISDICTIONS, coverage


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    cells = coverage(RULES)
    missing = 0
    out.write("%-4s %-10s " % ("jur", "side") + " ".join("%-17s" % i[:17] for i in INCOMES) + "\n")
    for jur in JURISDICTIONS:
        for side in ("source", "residence"):
            row = []
            for inc in INCOMES:
                kind, ids = cells[(jur, side, inc)]
                missing += kind == "MISSING"
                row.append("%-17s" % ({"CHARGE": "charge(%d)" % len(ids), "NOCHARGE": "nocharge", "SPLIT": "split", "MISSING": "-- MISSING --"}[kind]))
            out.write("%-4s %-10s %s\n" % (jur, side, " ".join(row)))
    out.write("%d cells, %d missing\n" % (len(cells), missing))
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
