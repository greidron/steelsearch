#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_jdk_readiness_translation_points_below_socketchannelimpl.py <socketchannelimpl-jdk-javap.txt>",
            file=sys.stderr,
        )
        return 2

    javap = Path(sys.argv[1]).read_text(errors="replace")

    has_translate_ready_ops = "public boolean translateReadyOps(int, int, sun.nio.ch.SelectionKeyImpl);" in javap
    has_pollerr = "Field sun/nio/ch/Net.POLLERR:S" in javap
    has_pollhup = "Field sun/nio/ch/Net.POLLHUP:S" in javap
    has_pollin = "Field sun/nio/ch/Net.POLLIN:S" in javap
    has_connected_check = "Method isConnected:()Z" in javap
    has_readyops_writeback = "Method sun/nio/ch/SelectionKeyImpl.nioReadyOps:(I)V" in javap
    has_translate_interest_ops = "public int translateInterestOps(int);" in javap

    print(f"has_translate_ready_ops={has_translate_ready_ops}")
    print(f"has_pollerr={has_pollerr}")
    print(f"has_pollhup={has_pollhup}")
    print(f"has_pollin={has_pollin}")
    print(f"has_connected_check={has_connected_check}")
    print(f"has_readyops_writeback={has_readyops_writeback}")
    print(f"has_translate_interest_ops={has_translate_interest_ops}")

    if (
        has_translate_ready_ops
        and has_pollerr
        and has_pollhup
        and has_pollin
        and has_connected_check
        and has_readyops_writeback
        and has_translate_interest_ops
    ):
        print(
            "checker_result="
            "socketchannelimpl_would_surface_pollin_or_hup_or_err_as_ready_ops_"
            "so_current_missing_signal_points_below_jdk_readiness_translation"
        )
        return 0

    print("checker_result=inconclusive_socketchannelimpl_contract")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
