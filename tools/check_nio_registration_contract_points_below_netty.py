#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_nio_registration_contract_points_below_netty.py "
            "<abstract-nio-channel-netty-javap.txt> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    javap = Path(sys.argv[1]).read_text(errors="replace")
    stdout = Path(sys.argv[2]).read_text(errors="replace")

    has_non_blocking_config = "SelectableChannel.configureBlocking:(Z)" in javap
    has_registration_field = "Field registration:Lio/netty/channel/IoRegistration;" in javap
    has_do_register = "protected void doRegister(io.netty.channel.ChannelPromise);" in javap
    has_do_begin_read = "protected void doBeginRead() throws java.lang.Exception;" in javap
    has_registration_validity_check = "InterfaceMethod io/netty/channel/IoRegistration.isValid:()Z" in javap
    has_add_and_submit = "Method addAndSubmit:(Lio/netty/channel/nio/NioIoOps;)V" in javap
    has_read_pending_true = "Field readPending:Z" in javap and "iconst_1" in javap

    write_ports = {
        int(m.group(1))
        for m in re.finditer(
            r"steelsearch_netty4_tcpchannel_stage=before_write_and_flush "
            r".*?local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:\d+ bytesLength=55",
            stdout,
        )
    }
    read_ports = {
        int(m.group(1))
        for m in re.finditer(
            r"steelsearch_netty4_message_channel_stage=channel_read .*?local=/127\.0\.0\.1:(\d+)",
            stdout,
        )
    }
    handshake_timeout = stdout.count("handshake_timeout[1s]")

    print(f"has_non_blocking_config={has_non_blocking_config}")
    print(f"has_registration_field={has_registration_field}")
    print(f"has_do_register={has_do_register}")
    print(f"has_do_begin_read={has_do_begin_read}")
    print(f"has_registration_validity_check={has_registration_validity_check}")
    print(f"has_add_and_submit={has_add_and_submit}")
    print(f"has_read_pending_true={has_read_pending_true}")
    print(f"write_ports={len(write_ports)}")
    print(f"write_read_overlap={len(write_ports & read_ports)}")
    print(f"handshake_timeout={handshake_timeout}")

    if (
        has_non_blocking_config
        and has_registration_field
        and has_do_register
        and has_do_begin_read
        and has_registration_validity_check
        and has_add_and_submit
        and has_read_pending_true
        and len(write_ports) > 0
        and len(write_ports & read_ports) == 0
        and handshake_timeout > 0
    ):
        print(
            "checker_result="
            "nio_registration_and_read_interest_contract_exist_so_current_missing_signal_"
            "points_below_netty_registration_and_toward_selector_ready_visibility"
        )
        return 0

    print("checker_result=inconclusive_registration_contract")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
