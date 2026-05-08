#!/usr/bin/env python3
import json
import shutil
from pathlib import Path


def main() -> int:
    profile_dir = Path('/tmp/osnode-selfprofile')
    raw_files = sorted(profile_dir.glob('*.mm_profdata'))
    summarize_path = shutil.which('summarize')
    crox_path = shutil.which('crox')

    result = {
        'profile_dir_exists': profile_dir.is_dir(),
        'raw_profile_file_count': len(raw_files),
        'raw_profile_files': [str(p) for p in raw_files],
        'summarize_in_path': summarize_path is not None,
        'crox_in_path': crox_path is not None,
        'result': 'self_profile_raw_artifact_is_reachable_but_query_level_analysis_is_currently_blocked_by_missing_measureme_summary_tools',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
