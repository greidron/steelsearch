#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_remote_address_setter_points_to_call_boundary_not_complex_semantics.py <javap.txt> <stdout.log>"
        )
        return 2

    javap_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    source_has_remote_address_setter = "public io.netty.bootstrap.Bootstrap remoteAddress(java.net.SocketAddress);" in javap_text
    source_has_putfield = "putfield      #8                  // Field remoteAddress:Ljava/net/SocketAddress;" in javap_text
    source_has_simple_return = "5: aload_0" in javap_text and "6: areturn" in javap_text

    before_remote = stdout_text.count("steelsearch_netty4_open_stage=before_remote_address")
    after_remote = stdout_text.count("steelsearch_netty4_open_stage=after_remote_address")
    after_handler = stdout_text.count("steelsearch_netty4_open_stage=after_handler_setter")

    print(f"source_has_remote_address_setter={source_has_remote_address_setter}")
    print(f"source_has_putfield={source_has_putfield}")
    print(f"source_has_simple_return={source_has_simple_return}")
    print(f"after_handler_setter={after_handler}")
    print(f"before_remote_address={before_remote}")
    print(f"after_remote_address={after_remote}")

    if (
        source_has_remote_address_setter
        and source_has_putfield
        and source_has_simple_return
        and after_handler > 0
        and before_remote > 0
        and after_remote == 0
    ):
        print(
            "checker_result=remoteAddress_is_a_trivial_setter_so_current_stop_points_to_call_boundary_or_broader_runtime_divergence_not_complex_setter_semantics"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
