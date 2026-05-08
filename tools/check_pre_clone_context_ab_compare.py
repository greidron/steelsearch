#!/usr/bin/env python3
import re
import sys
from pathlib import Path


PATTERN = re.compile(
    r"steelsearch_netty4_open_stage=pre_clone_context thread=(?P<thread>\S+) "
    r"threadId=(?P<thread_id>\d+) interrupted=(?P<interrupted>\S+) "
    r"bootstrapHash=(?P<bootstrap>\d+) configHash=(?P<config>\d+) "
    r"groupHash=(?P<group>\d+) handlerHash=(?P<handler>\d+) "
    r"channelFactory=(?P<factory>\S+) remote=(?P<remote>.+)$"
)


def parse(path: str) -> dict[str, str]:
    text = Path(path).read_text().splitlines()
    result: dict[str, str] = {}
    for line in text:
        match = PATTERN.search(line)
        if match:
            result = match.groupdict()
            break
    result["after_clone"] = str(Path(path).read_text().count("steelsearch_netty4_open_stage=after_clone"))
    result["before_direct_ctor"] = str(Path(path).read_text().count("steelsearch_netty4_open_stage=before_direct_nio_ctor"))
    return result


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_pre_clone_context_ab_compare.py <run-a.log> <run-b.log>", file=sys.stderr)
        return 2

    a = parse(sys.argv[1])
    b = parse(sys.argv[2])

    for prefix, data in (("run_a", a), ("run_b", b)):
        for key in ("thread", "thread_id", "interrupted", "bootstrap", "config", "group", "handler", "factory", "remote", "after_clone", "before_direct_ctor"):
            print(f"{prefix}_{key}={data.get(key, '')}")

    same_context = all(
        a.get(key) == b.get(key)
        for key in ("thread", "interrupted", "bootstrap", "config", "group", "handler", "factory", "remote")
    )
    diverged_outcome = a.get("before_direct_ctor") != b.get("before_direct_ctor") or a.get("after_clone") != b.get("after_clone")

    if same_context and diverged_outcome:
        print("checker_result=same_pre_clone_context_but_diverged_outcome_points_to_runtime_nondeterminism")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
