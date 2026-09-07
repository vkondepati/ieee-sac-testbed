#!/usr/bin/env python3
from _common import FIXTURE, RESULTS, load_contract, load_queries, write_json
from saccloud.normalize import scalar
from saccloud.reference_evaluator import evaluate_all


def conv(x):
    if isinstance(x, dict): return {k: conv(v) for k, v in x.items()}
    if isinstance(x, list): return [conv(v) for v in x]
    return scalar(x)

out = conv(evaluate_all(load_contract(), FIXTURE, load_queries()))
write_json(RESULTS / "reference.json", out)
print("Wrote", RESULTS / "reference.json")
