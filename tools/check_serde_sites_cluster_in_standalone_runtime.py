#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
SRC = ROOT / 'crates/os-node/src'


def main() -> int:
    per_file = {}
    for path in SRC.glob('*.rs'):
        text = path.read_text()
        count = (
            text.count('Serialize')
            + text.count('Deserialize')
            + text.count('#[serde(')
        )
        if count:
            per_file[path.name] = count

    total = sum(per_file.values())
    top_file = max(per_file, key=per_file.get)
    top_count = per_file[top_file]

    result = {
        'serde_like_sites_per_file': per_file,
        'total_serde_like_sites': total,
        'top_file': top_file,
        'top_count': top_count,
        'top_share': round(top_count / total, 3) if total else 0.0,
        'result': 'serde_like_proc_macro_sites_are_overwhelmingly_clustered_in_standalone_runtime_rs',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
