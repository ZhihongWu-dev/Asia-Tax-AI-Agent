"""All rule specs compiled together (规则层.md §4). Add a jurisdiction by appending its SPEC."""
from . import spec_cn, spec_hk, spec_sg

SPEC = spec_sg.SPEC + spec_cn.SPEC + spec_hk.SPEC
