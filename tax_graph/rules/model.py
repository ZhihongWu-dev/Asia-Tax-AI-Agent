"""Rule objects: the compiled layer between official/ and the engine (规则层.md §1).

A spec writes five things per rule (id, scope, effect, value, cond) plus optional overrides, readings and the
parameters a procedure evaluator uses. Everything else is derived by compile.py. Specs hold no numbers.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Callable, FrozenSet, Optional, Tuple


class Grade(Enum):
    A_TEXT = 1              # value and conditions quoted from the text (params.csv)
    B_PRACTICE = 2          # seen only in an official tool or administrative practice (observed_rules.csv)
    C_READING = 3           # the text allows two readings (spec.readings)
    D_DISCRETION = 4        # facts-and-circumstances judgement (Discretion leaf)


class Effect(Enum):
    CHARGE = "CHARGE"       # creates a tax item at the domestic rate
    BASE = "BASE"           # multiplies the taxable base (e.g. 60% of equipment rent)
    RATE_CAP = "RATE_CAP"   # rate = min(rate, cap)
    EXEMPT = "EXEMPT"       # rate = 0
    CREDIT = "CREDIT"       # residence item: credit for the source tax on the same income, limited to the residence tax on it
    DEFER = "DEFER"         # entity stage
    DEADLINE = "DEADLINE"   # procedure: a date on the label
    PENALTY = "PENALTY"     # procedure: an amount on the label
    DENY = "DENY"           # no effect of its own: suppresses the rules it overrides (anti-abuse)
    DEDUCTION = "DEDUCTION" # the payer deducts the payment: a negative item at the payer's corporate rate
    NOCHARGE = "NOCHARGE"   # a declaration, with a cite, that this jurisdiction levies nothing on this cell (场景.md §3)
    SPLIT = "SPLIT"         # a declaration that this income is decomposed into other incomes before any rule applies
    DEDUCT_BASE = "DEDUCT_BASE"   # scales the payer's deduction (benchmark interest, arm's-length cap)
    STAMP = "STAMP"         # a levy on the instrument, by the taxing jurisdiction, borne by the side the rule names
    VAT = "VAT"             # a turnover-tax item: withheld from the payee, or the payer's input credit (negative)


STAGES = (Effect.NOCHARGE, Effect.SPLIT, Effect.VAT, Effect.CHARGE, Effect.BASE, Effect.RATE_CAP, Effect.EXEMPT, Effect.CREDIT, Effect.DEFER,
          Effect.DEDUCTION, Effect.DEDUCT_BASE, Effect.STAMP)   # on an edge, in this order; VAT first: an income tax on a
                                                                # VAT-inclusive price is on the price net of the VAT (口径 D26)
ENTITY_STAGES = ()                                # pooled credits across flows (SG s50C) would live here; not in v1
PROCEDURE = (Effect.DEADLINE, Effect.PENALTY)
NON_COMMUTING = (Effect.CHARGE, Effect.BASE)      # two of these on one scope must be linked by overrides


class Mount(Enum):
    ENTITY = "ENTITY"
    FLOW = "FLOW"
    PATH = "PATH"
    SUBGRAPH = "SUBGRAPH"


ALL = "ALL"


@dataclass(frozen=True)
class Pred:
    name: str
    fn: Callable[[object, object], bool]
    needs_param: bool = True

    def __call__(self, value, threshold):
        return self.fn(value, threshold)


is_true = Pred("is_true", lambda v, t: v is True, needs_param=False)
is_false = Pred("is_false", lambda v, t: v is False, needs_param=False)
ge = Pred("ge", lambda v, t: v >= t)
gt = Pred("gt", lambda v, t: v > t)
le = Pred("le", lambda v, t: v <= t)
lt = Pred("lt", lambda v, t: v < t)
eq = Pred("eq", lambda v, t: v == t)
is_in = Pred("is_in", lambda v, t: v in str(t).split(";"))     # enum parameter "a;b;c"


@dataclass(frozen=True)
class Scope:
    source: str                         # where the income arises = payer.loc; ALL = any
    residence: Optional[str]            # payee's residence; None = domestic rule, no direction
    income: object                      # Income name, a tuple of names, or ALL
    mount: Mount = Mount.FLOW
    side: str = "source"                # which jurisdiction's tax the rule acts on: source | residence | a jurisdiction code

    def covers(self, income):
        return self.income == ALL or income == self.income or (isinstance(self.income, tuple) and income in self.income)

    @property
    def taxing(self):
        if self.side == "residence":
            return self.residence
        return self.source if self.side == "source" else self.side


@dataclass(frozen=True)
class Leaf:
    field: str
    pred: Pred
    param: Optional[str] = None         # threshold comes from params.csv, never from the spec
    on: str = "flow"                    # flow | payer | payee | hold


@dataclass(frozen=True)
class Discretion:
    key: str
    cites: Tuple[str, ...] = ()         # the factors the authority lists; carried into the conditions output
    on: str = "payee"


class And:
    __slots__ = ("xs",)

    def __init__(self, *xs):
        self.xs = tuple(xs)

    def __repr__(self):
        return "And(%s)" % ", ".join(map(repr, self.xs))


class Or:
    __slots__ = ("xs",)

    def __init__(self, *xs):
        self.xs = tuple(xs)

    def __repr__(self):
        return "Or(%s)" % ", ".join(map(repr, self.xs))


class Not:
    __slots__ = ("x",)

    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return "Not(%r)" % (self.x,)


ALWAYS = And()                          # an empty conjunction is true


@dataclass(frozen=True)
class RuleObj:
    # written in the spec
    id: str
    scope: Scope
    effect: Effect
    value: Optional[str]                # param_id, or "observed:<rule_id>" for grade B
    cond: object = ALWAYS
    overrides: FrozenSet[str] = frozenset()
    readings: Tuple[object, ...] = ()   # a second reading of the same text makes the rule grade C
    uses: Tuple[str, ...] = ()          # params a procedure evaluator reads besides value
    bearer: Optional[str] = None        # STAMP: "payer" (the buyer) or "payee" (the seller) bears the levy
    ambiguous: bool = False             # its direction depends on the numbers (a recharacterisation): decided by comparing both outcomes
    before: Tuple[str, ...] = ()        # 口径 D30: (law, clause) when its law replaced rules the library does not keep — a flow
                                        # dated before the rule takes effect is outside the library for its levy
    # derived by compile.py
    reads: FrozenSet[str] = frozenset()
    favourable: Optional[bool] = None
    grade: Optional[Grade] = None
    sources: Tuple[str, ...] = ()
    valid: Tuple[Optional[date], Optional[date]] = (None, None)


def leaves(c):
    """All Leaf and Discretion nodes of a condition tree."""
    if isinstance(c, (Leaf, Discretion)):
        return [c]
    if isinstance(c, (And, Or)):
        return [x for y in c.xs for x in leaves(y)]
    if isinstance(c, Not):
        return leaves(c.x)
    raise TypeError("not a condition: %r" % (c,))
