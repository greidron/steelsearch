#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_netty_read_interest_contract_points_to_missing_selector_ready.py "
            "<abstract-nio-byte-channel-javap.txt> <default-channel-config-javap.txt>",
            file=sys.stderr,
        )
        return 2

    byte_channel = Path(sys.argv[1]).read_text(errors="replace")
    default_cfg = Path(sys.argv[2]).read_text(errors="replace")

    has_should_break = "shouldBreakReadReady" in byte_channel
    should_break_checks_input_shutdown = "Method isInputShutdown0" in byte_channel
    should_break_checks_half_closure = "isAllowHalfClosure" in byte_channel
    do_begin_read_sets_pending = "putfield      #46                 // Field readPending:Z" in Path(
        "/tmp/abstract-nio-channel-netty-javap.txt"
    ).read_text(errors="replace") and "Method addAndSubmit" in Path("/tmp/abstract-nio-channel-netty-javap.txt").read_text(
        errors="replace"
    )
    auto_read_defaults_true = "putfield      #15                 // Field autoRead:I" in default_cfg and "38: iconst_1" in default_cfg

    print(f"has_should_break={has_should_break}")
    print(f"should_break_checks_input_shutdown={should_break_checks_input_shutdown}")
    print(f"should_break_checks_half_closure={should_break_checks_half_closure}")
    print(f"do_begin_read_sets_pending={do_begin_read_sets_pending}")
    print(f"auto_read_defaults_true={auto_read_defaults_true}")

    if (
        has_should_break
        and should_break_checks_input_shutdown
        and should_break_checks_half_closure
        and do_begin_read_sets_pending
        and auto_read_defaults_true
    ):
        print(
            "checker_result="
            "netty_read_interest_contract_points_away_from_autoread_removeReadOp_gating_"
            "and_toward_missing_selector_ready_before_timeout"
        )
        return 0

    print("checker_result=inconclusive_contract_split")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
