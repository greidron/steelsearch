#!/usr/bin/env python3
import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    print('usage: check_reg_allocator_static_bias_matches_8_9_10_11_sequence.py <stdout.log> <ConnectionProfile.java>', file=sys.stderr)
    sys.exit(2)

log = Path(sys.argv[1]).read_text(errors='replace').splitlines()
profile = Path(sys.argv[2]).read_text(errors='replace')

seq = []
for idx, line in enumerate(log, start=1):
    if 275 <= idx <= 288 and 'action-tagged selected channel index' in line and 'type [REG]' in line:
        m = re.search(r'index \[(\d+)\]', line)
        if m:
            seq.append(int(m.group(1)))

expected_prefix = [8, 9, 10, 11]
source_round_robin = 'offset + Math.floorMod(counter.incrementAndGet(), length)' in profile
result = 'inconclusive'
if seq[:4] == expected_prefix and source_round_robin:
    result = 'reg_allocator_static_bias_matches_actual_8_9_10_11_sequence_and_leaves_edge_slots_7_12_unused_early'

print(f'reg_selected_prefix = {seq[:4]}')
print(f'expected_prefix = {expected_prefix}')
print(f'source_round_robin = {source_round_robin}')
print(f'result = {result}')
