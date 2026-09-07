#!/usr/bin/env python3
from _common import OBS, RESULTS, write_json
from saccloud.observability import summarize
r=summarize(OBS);write_json(RESULTS/"observability_summary.json",r)
for k,v in r.items(): print(f"{k}: {v}")
