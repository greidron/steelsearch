## mixed Java data-node actual run blocker

2026-05-06 source-level formed producer restore candidate update

- rust low-level tcp handshake response 뒤 special `400ms` follow-up peek가 restore blocker인지 보려고
  - `STEELSEARCH_TCP_HANDSHAKE_DIRECT_HOLD_OPEN_AFTER_RESPONSE=1`
  - source gate를 추가해 바로 `hold_transport_channel_open(...)`으로 들어가게 했다.
- actual probe `/tmp/java-rust-mixed-membership.direct-hold-open` 결과는
  - `membership_formed=false`
  - `observed_node_count=0`
  - formed-only handoff 미생성
  - `tcp_total=17`
  - `follow_up_count=0`
  - `remote_eof_count=17`
  로 zero-node baseline과 동일했다.
- 의미:
  - current fresh formed producer regression은 rust-side post-response `400ms` follow-up peek contract 자체로는 설명되지 않는다.
  - 다음 source-level candidate는 generic rust post-response wait contract보다
    - Java explicit local close/read-starvation에 영향을 줄 수 있는 path
    - 또는 rust response 직후 Java read wakeup을 더 직접 자극하는 path
    쪽이 더 생산적이다.

2026-05-06 immediate proactive ping restore candidate update

- rust low-level tcp handshake response 직후 Java read wakeup을 직접 자극해 보려고
  - `STEELSEARCH_TCP_HANDSHAKE_IMMEDIATE_PROACTIVE_PING_AFTER_RESPONSE=1`
  - source gate를 추가해 response flush 직후 keepalive ping을 한 번 더 쓰게 했다.
- actual probe `/tmp/java-rust-mixed-membership.immediate-ping` 결과는
  - `membership_formed=false`
  - `observed_node_count=0`
  - formed-only handoff 미생성
  - `follow_up_count=0`
  - `response_read=0`
  - `internal:transport/handshake send meta=0`
  였다.
- baseline 대비 달라진 것은
  - `proactive_keepalive_total=0 -> 16`
  뿐이며, formed handoff나 Java promotion path는 여전히 열리지 않았다.
- 의미:
  - immediate Rust-side post-response ping도 Java low-level response observation/read-starvation collapse를 복구하지 못한다.
  - 다음 source-level candidate는 Rust post-response stimulation보다 Java-side timeout/close gate나 low-level response consumption gate에 더 직접 닿아야 한다.

2026-05-06 forced low-level handshake success-on-timeout candidate update

- OpenSearch `TransportHandshaker` timeout callback에
  - `STEELSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_ON_TIMEOUT=1`
  - gate를 넣어 timeout 시 synthetic low-level handshake success로 promotion을 강제하려 했다.
- probe wrapper도
  - `JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_ON_TIMEOUT`
  - 를 child OpenSearch env로 pass-through 하도록 보강했다.
- actual probe `/tmp/java-rust-mixed-membership.force-handshake-success-pass` 결과는
  - `membership_formed=false`
  - `observed_node_count=0`
  - formed-only handoff 미생성
  - zero-node baseline과 동일한 `tcp_total=17`, `follow_up_count=0`, `remote_eof_count=17`
  이었다.
- 추가로 `opensearch/launch-env.json`에는 gate env가 실제로 기록됐지만 stdout marker는
  - `force_success_on_timeout=0`
  - `handle_response=0`
  - `execute_handshake_listener_onResponse=0`
  - `execute_handshake_listener_onFailure=67`
  였다.
- 의미:
  - current collapse는 이 timeout callback gate를 실제로 타기 전에 이미 다른 failure path로 정리될 가능성이 높다.
  - 다음 source-level candidate는 `TransportHandshaker` timeout callback보다 더 앞선 Java-side low-level response consumption / onFailure dispatch gate에 직접 닿아야 한다.

2026-05-06 executeHandshake listener onFailure force-success candidate update

- OpenSearch `TcpTransport.executeHandshake(...)`의 `listener.onFailure` branch에
  - `STEELSEARCH_FORCE_EXECUTE_HANDSHAKE_LISTENER_SUCCESS_ON_FAILURE=1`
  - gate를 넣어 onFailure 시 synthetic success로 promotion을 강제하려 했다.
- probe wrapper도
  - `JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_FORCE_EXECUTE_HANDSHAKE_LISTENER_SUCCESS_ON_FAILURE`
  - 를 child OpenSearch env로 pass-through 하도록 보강했다.
- actual probe `/tmp/java-rust-mixed-membership.force-exec-success` 결과는
  - `membership_formed=false`
  - `observed_node_count=0`
  - formed-only handoff 미생성
  - zero-node baseline과 동일한 `tcp_total=17`, `follow_up_count=0`, `remote_eof_count=17`
  이었다.
- 추가로
  - `opensearch/launch-env.json`에는 gate env가 실제로 기록됐고
  - `execute_handshake_listener_onFailure=49`는 찍혔지만
  - 같은 lambda 안에 추가한 `execute_handshake_listener_force_success_onFailure=0`
  - `execute_handshake_listener_onResponse=0`
  - `internal:transport/handshake send meta=0`
  이었다.
- 의미:
  - current active failure path는 `executeHandshake listener.onFailure` 인접 source patch로도 실질적으로 바뀌지 않았다.
  - 다음 source-level candidate는 Java-side listener branch injection보다 더 앞선 low-level response consumption / dispatch path 자체를 건드려야 할 가능성이 높다.

2026-05-06 immediate post-send synthetic handshake success candidate update

- OpenSearch `TransportHandshaker.sendHandshake(...)`의 `after_send_request` 직후에
  - `STEELSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_IMMEDIATELY_AFTER_SEND=1`
  - gate를 넣어 low-level response consumption 자체를 synthetic success로 바로 우회하려 했다.
- probe wrapper도
  - `JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_FORCE_LOW_LEVEL_HANDSHAKE_SUCCESS_IMMEDIATELY_AFTER_SEND`
  - 를 child OpenSearch env로 pass-through 하도록 보강했다.
- actual probe `/tmp/java-rust-mixed-membership.force-immediate-success` 결과는
  - `membership_formed=false`
  - `observed_node_count=0`
  - formed-only handoff 미생성
  - zero-node baseline과 동일한 `tcp_total=17`, `follow_up_count=0`, `remote_eof_count=17`
  이었다.
- 추가로
  - `opensearch/launch-env.json`에는 gate env가 실제로 기록됐지만
  - `force_success_immediately_after_send=0`
  - `handle_response=0`
  - `execute_handshake_listener_onResponse=0`
  - `internal:transport/handshake send meta=0`
  이었다.
- 의미:
  - current source-level restore family에서 `listener.onFailure` 인접 synthetic success도, `after_send_request` 직후 synthetic success도 active path를 실질적으로 바꾸지 못했다.
  - 다음 질문은 이 family를 practical stop으로 닫을지, 아니면 Java inbound response delivery/dispatch path에 더 직접 닿는 source patch 후보를 계속 캘 가치가 있는지다.

2026-05-06 source-level restore family practical stop update

- checker `check_source_level_restore_family_practical_stop.py`로
  - zero-node baseline `/tmp/java-rust-mixed-membership.formed-only-fresh.live.json`
  - source-level candidate family
    - `direct-hold-open`
    - `immediate-ping`
    - `force-handshake-success-pass`
    - `force-exec-success`
    - `force-immediate-success`
  - 기존 full read-starvation artifact `/tmp/java-rust-mixed-membership.H87Ghe/opensearch/stdout.log`
  를 함께 묶어 판정했다.
- 결과:
  - source-level candidate family 전부가 `membership_formed=false`, `observed_node_count=0`, `follow_up_count=0`
  - starvation artifact는 `response_read=0`, `handle_response=0`
  - checker result는 `source_level_restore_family_matches_existing_full_read_starvation_practical_stop`
  이었다.
- 의미:
  - current source-level formed producer restore family는 별도 새 해결축이라기보다, 이미 정리된 full OpenSearch read-starvation practical stop과 같은 branch로 보는 편이 맞다.
  - 다음 질문은 이 conclusion을 보존한 채 next productive branch를 어디로 둘지다.

2026-05-06 next branch after source-level restore stop update

- checker `check_next_branch_after_source_level_restore_stop.py`로
  - actual CRUD prepare gate artifact `/tmp/rust-primary-java-replica-readygate-direct/prepare-phase.json`
  - source-level restore stop matrix `/tmp/source-level-restore-stop.json`
  를 함께 판정했다.
- 결과:
  - `prepare_ready_gate=false`
  - `prepare_ready_node_count=0`
  - `prepare_ready_error=TimeoutError: timed out`
  - `source_level_stop_result=source_level_restore_family_matches_existing_full_read_starvation_practical_stop`
  - checker result `next_productive_branch_is_existing_java_inbound_response_delivery_read_starvation_branch_not_actual_run_backlog`
- 의미:
  - current session에서는 actual run backlog로 바로 가는 것보다, 이미 known practical stop인 Java inbound response delivery/read-starvation branch를 blocker root로 보는 편이 맞다.
  - 남은 질문은 이 branch가 이미 current session practical stop인 사실을 broader backlog에 어떻게 반영할지다.

2026-05-06 broader backlog blocker-root update

- checker `check_broader_backlog_after_read_starvation_stop.py`로
  - next-branch verdict `/tmp/next-branch-after-source-stop.json`
  - native selector stop verdict `/tmp/native-selector-stop.json`
  를 함께 판정했다.
- 결과:
  - `next_branch_result=next_productive_branch_is_existing_java_inbound_response_delivery_read_starvation_branch_not_actual_run_backlog`
  - `prepare_ready_gate=false`
  - `native_selector_stop_result=selector_boundary_reaches_native_poll_epoll_symbols_and_current_session_lacks_dynamic_visibility_so_this_branch_is_a_practical_stop_point`
  - checker result `current_session_should_record_read_starvation_as_blocking_backlog_root_pending_external_native_instrumentation`
- 의미:
  - current mixed actual run backlog는 read-starvation practical stop이 root blocker인 상태로 보는 편이 맞다.
  - current session에서 더 진행하려면 source patch family가 아니라 `strace` 또는 `perf raw_syscalls` 수준의 external native instrumentation 가시성이 먼저 필요하다.

2026-05-06 external native instrumentation blocker update

- checker `check_external_native_instrumentation_blocker.py`로
  - prepare gate artifact `/tmp/rust-primary-java-replica-readygate-direct/prepare-phase.json`
  - next-branch verdict `/tmp/next-branch-after-source-stop.json`
  - native selector stop verdict `/tmp/native-selector-stop.json`
  를 함께 판정했다.
- 결과:
  - `prepare_ready_gate=false`
  - `prepare_ready_node_count=0`
  - `next_branch_result=next_productive_branch_is_existing_java_inbound_response_delivery_read_starvation_branch_not_actual_run_backlog`
  - `native_selector_stop_result=selector_boundary_reaches_native_poll_epoll_symbols_and_current_session_lacks_dynamic_visibility_so_this_branch_is_a_practical_stop_point`
  - checker result `external_native_instrumentation_is_the_current_blocker_and_actual_run_backlog_remains_blocked`
- 의미:
  - current session에서는 actual run backlog가 코드 경로보다 environment capability에 의해 막혀 있다.
  - 다음 생산적 step은 source patch 추가보다 `strace` 또는 `perf raw_syscalls` 가시성이 있는 환경에서 read-starvation branch를 재개하는 것이다.

2026-05-06 current environment instrumentation availability update

- checker `check_current_env_external_native_instrumentation_unavailable.py`로 current session의 instrumentation capability를 actual로 확인했다.
- 결과:
  - `strace_path=null`
  - `perf_raw_syscalls_available=false`
  - `perf_probe_exit_code=129`
  - stderr는 `can't access trace events` / `No permissions to read /sys/kernel/tracing/...`
  - checker result `current_environment_lacks_external_native_instrumentation_needed_to_resume_read_starvation_branch`
- 의미:
  - current session에서는 read-starvation branch를 실제로 재개할 수 없다.
  - 다음 질문은 capable env를 어떻게 확보하거나 연결하느냐이다.

2026-05-06 current environment self-provision gap update

- checker `check_current_env_cannot_self_provision_native_instrumentation.py`로 current session이 external native instrumentation 환경을 스스로 만들 수 있는지도 actual로 확인했다.
- 결과:
  - `uid=1001`
  - `strace_path=null`
  - `apt_get_path=/usr/bin/apt-get`
  - `/sys/kernel/tracing exists=true, writable=false`
  - `/sys/kernel/tracing/events/raw_syscalls/sys_enter exists=true, writable=false`
  - `perf_raw_syscalls_available=false`
  - `perf_probe_exit_code=129`
  - checker result `current_environment_cannot_self_provision_external_native_instrumentation_for_read_starvation_branch`
- 의미:
  - current session은 non-root이고 tracing fs write 권한도 없어, `apt-get` 존재만으로는 capable env를 자력 복구할 수 없다.
  - 따라서 다음 blocker는 code path가 아니라 external capable env handoff다:
    - root-enabled tracing
    - 또는 preinstalled `strace`
    - 또는 usable `perf raw_syscalls`

2026-05-06 local sudo perf capability update

- 위 self-provision gap 이후, local host에 non-interactive `sudo`가 실제로 열려 있는지와 `sudo perf raw_syscalls`가 usable한지를 별도 checker `check_local_sudo_perf_capable_env.py`로 다시 확인했다.
- 결과:
  - `sudo_non_interactive_available=true`
  - `sudo_probe_exit_code=0`
  - `strace_path=null`
  - `perf_raw_syscalls_via_sudo_available=true`
  - `perf_probe_exit_code=0`
  - checker result `local_sudo_perf_raw_syscalls_capable_environment_is_available_for_read_starvation_branch`
- 의미:
  - external host handoff가 유일한 선택지는 아니다.
  - current host 자체가 `sudo perf raw_syscalls` 기준으로는 이미 capable env다.
  - 따라서 다음 직접 작업은 env 확보가 아니라, 이 local sudo-perf path로 Java inbound response delivery/read-starvation branch를 실제 재개하는 것이다.

2026-05-06 local sudo perf failing-probe resume update

- collector `run_probe_with_sudo_perf_stat.py`를 추가해 fresh failing probe `/tmp/java-rust-mixed-membership.sudo-perf-2`에 실제로 `sudo perf stat`를 attach했다.
- summary `/tmp/java-rust-mixed-membership.sudo-perf-2-summary.json` 결과:
  - `perf_returncode=0`
  - `perf_counts.sys_enter=182000`
  - `perf_counts.sys_exit=181954`
  - `probe_returncode=1`
  - `report_membership_formed=false`
  - `report_failure_stage=membership_timeout`
  - `report_observed_node_count=0`
  - checker result `sudo_perf_stat_collected_on_failing_probe`
- 의미:
  - current session에서 read-starvation failing probe 위에 local `sudo perf raw_syscalls` instrumentation을 실제로 얹는 것까지는 성공했다.
  - 다만 현재 artifact는 aggregate syscall count만 주므로, 다음 직접 질문은 per-syscall mix다:
    - `epoll_wait`
    - `read`
    - `close`
    - timeout window ordering

2026-05-06 local sudo perf trace mix update

- collector `run_probe_with_sudo_perf_trace.py`를 추가해 fresh failing probe `/tmp/java-rust-mixed-membership.sudo-trace-3`에 실제로 `sudo perf trace`를 붙였다.
- summary `/tmp/java-rust-mixed-membership.sudo-trace-3-summary.json` 결과:
  - `trace_returncode=0`
  - `syscall_counts.read=2`
  - `syscall_counts.close=1`
  - `syscall_counts.epoll_pwait=0`
  - `syscall_counts.epoll_pwait2=0`
  - `probe_returncode=1`
  - `report_membership_formed=false`
  - `report_failure_stage=membership_timeout`
  - checker result `sudo_perf_trace_collected_on_failing_probe`
- 의미:
  - current session에서 local `sudo perf trace` 기반 per-syscall mix artifact 확보까지는 성공했다.
  - 다만 이번 sample window는 짧았고 `epoll_*`가 0으로 남았으므로, 다음 직접 질문은 timeout 직전까지 더 긴 trace window에서 `read/close/epoll_*` ordering을 어떻게 다시 잡느냐이다.

2026-05-06 local sudo perf trace longer-window update

- 같은 collector로 fresh failing probe `/tmp/java-rust-mixed-membership.sudo-trace-15s`에 `trace_duration_ms=15000` longer window를 실제로 다시 적용했다.
- summary `/tmp/java-rust-mixed-membership.sudo-trace-15s-summary.json` 결과:
  - `trace_returncode=0`
  - `syscall_counts.read=13`
  - `syscall_counts.close=16`
  - `syscall_counts.epoll_pwait=0`
  - `syscall_counts.epoll_pwait2=0`
  - `report_membership_formed=false`
  - `report_failure_stage=membership_timeout`
  - checker result `sudo_perf_trace_collected_on_failing_probe`
- 의미:
  - longer failing window에서도 `read/close`는 실제로 잡힌다.
  - 반면 현재 selector set의 `epoll_pwait/epoll_pwait2`는 여전히 0이다.
  - 따라서 다음 직접 질문은 Java selector wait syscall이
    - 정말 `epoll_*`를 안 쓰는지
    - 아니면 현재 selector set이 빗나간 건지
    를 `futex/poll/ppoll`까지 넓혀 actual로 다시 좁히는 것이다.

2026-05-06 local sudo perf widened wait-family update

- widened subset run `/tmp/java-rust-mixed-membership.sudo-trace-wide-2`에서 events
  - `syscalls:sys_enter_read`
  - `syscalls:sys_enter_close`
  - `futex`
  - `ppoll`
  - `epoll_pwait`
  - `epoll_pwait2`
  를 actual로 다시 수집했다.
- summary `/tmp/java-rust-mixed-membership.sudo-trace-wide-2-summary.json` 결과:
  - `trace_returncode=0`
  - `read=13`
  - `close=16`
  - `futex=1`
  - `ppoll=0`
  - `epoll_pwait=0`
  - `epoll_pwait2=0`
  - `report_failure_stage=membership_timeout`
- 의미:
  - current failing window에서 wait-family signal은 `futex=1`만 보이고, `ppoll/epoll_*`는 보이지 않는다.
  - 따라서 다음 직접 질문은 이 `futex=1`이 selector thread wait인지, 아니면 unrelated Java thread wait인지다.

2026-05-06 local sudo perf record futex stack update

- collector `run_probe_with_sudo_perf_record.py`로 fresh failing probe `/tmp/java-rust-mixed-membership.sudo-record-futex`에서 `perf record -g -e syscalls:sys_enter_futex`를 actual로 수집했다.
- summary `/tmp/java-rust-mixed-membership.sudo-record-futex-summary.json` 결과:
  - `record_returncode=0`
  - `script_returncode=0`
  - `futex_event_count=30274`
  - `report_failure_stage=membership_timeout`
  - checker result `sudo_perf_record_futex_thread_identity_collected_on_failing_probe`
- 이어 checker `check_futex_record_points_to_startup_monitor_waits.py`로 `sudo-perf-record-futex.script.txt`를 판정한 결과:
  - `futex_event_headers=10603`
  - `startup_monitor_wait_symbol_hits=802`
  - top stack symbols에 `pthread_cond_wait`, `PlatformMonitor::wait`, `Monitor::wait_without_safepoint_check`, `thread_native_entry`가 실제로 잡힘
  - checker result `futex_record_points_more_directly_to_java_startup_monitor_waits_than_selector_epoll_wait`
- 의미:
  - widened trace에서 보인 `futex=1`은 selector epoll wait라기보다 Java startup/monitor wait noise 쪽에 더 가깝다.
  - 따라서 다음 직접 질문은 startup noise를 빼고 OpenSearch startup 이후 late failing window만 따로 record하면 selector-wait family가 보이느냐이다.

2026-05-06 local sudo perf late-window selector wait update

- collector `run_probe_with_sudo_perf_trace.py`에 `--late-start-after-http-ready-seconds` gate를 추가해 OpenSearch HTTP ready 이후 20초를 기다린 다음 widened selector trace를 actual로 수집했다.
- fresh run `/tmp/java-rust-mixed-membership.sudo-trace-late` summary `/tmp/java-rust-mixed-membership.sudo-trace-late-summary.json` 결과:
  - `http_ready_before_trace=true`
  - `late_start_after_http_ready_seconds=20`
  - `read=344`
  - `close=240`
  - `futex=3770`
  - `ppoll=8`
  - `epoll_pwait=139`
  - `epoll_pwait2=0`
  - `report_failure_stage=membership_timeout`
  - checker result `sudo_perf_trace_collected_on_failing_probe`
- 의미:
  - startup noise를 뺀 late failing window에서는 selector-wait family로 `epoll_pwait`가 실제로 보인다.
  - 따라서 next direct question은 “selector thread가 실제로 `epoll_pwait`만 하고 same-thread `read` delivery를 못 하는가”를 thread-aware artifact로 다시 묶는 것이다.

2026-05-06 late perf thread-overlap update

- late-thread collector `run_probe_with_sudo_perf_record_late_threads.py`로 fresh run `/tmp/java-rust-mixed-membership.sudo-record-late-threads`를 actual로 수집했다.
- 이어 checker `check_late_perf_script_same_thread_overlap.py`로 `sudo-perf-record-late-threads.script.txt`를 판정한 결과:
  - `thread_count=7`
  - `wait_only_threads=[]`
  - `overlap_threads`:
    - `tid=313786 read=16 close=3 epoll_pwait=26`
    - `tid=313794 read=19 close=3 epoll_pwait=28`
    - `tid=313799 read=22 close=2 epoll_pwait=25`
  - checker result `late_perf_script_shows_same_thread_epoll_wait_and_read_overlap`
- 의미:
  - late failing window의 selector-like threads는 `epoll_pwait`만 하는 것이 아니라 same-thread `read`도 실제로 수행한다.
  - 따라서 남은 direct question은 “same-thread read가 실제로 있었는데 왜 Netty `channelRead` marker는 same socket에서 0인가”이며, 다음 직접 축은 thread role/FD correlation이다.

2026-05-07 late thread/FD correlation update

- checker `check_late_overlap_reads_are_control_fd_not_socket_payload.py`로 `/tmp/java-rust-mixed-membership.sudo-record-late-threads/opensearch/sudo-perf-record-late-threads.script.txt`의 FD/size pattern을 actual로 파싱했다.
- 결과:
  - overlap threads:
    - `tid=313786`: `epfd=181`, `read_fds=182(16-byte x14), 191(2048-byte x2)`
    - `tid=313794`: `epfd=183`, `read_fds=184(16-byte x16), 191(2048-byte x3)`
    - `tid=313799`: `epfd=185`, `read_fds=186(16-byte x12), 156(30-byte x4 / 1581-byte x2 / 3401-byte x1), 191(2048-byte x2)`
  - read-only threads `313787/313791/313792/313793`는 `fd=191/193/194`에서 주로 `1024/2048/8192-byte` payload reads를 수행
  - checker result `late_overlap_fd_pattern_did_not_cleanly_separate_control_reads_from_payload_reads`
- 의미:
  - overlap thread read는 control-sized 16-byte read가 주류이긴 하지만, payload-sized read도 일부 섞여 있다.
  - 따라서 남은 직접 질문은 specific FD role mapping이다:
    - `fd=191/193/194`가 각각 어떤 socket role인지
    - `epfd=181/183/185`와 어떤 late-thread 조합으로 연결되는지
    - starvation same socket read가 실제로 어느 thread/FD 조합에서 일어나는지

2026-05-07 late FD snapshot mapping update

- collector `run_probe_with_fd_snapshot_and_perf_late_threads.py`로 fresh run `/tmp/java-rust-mixed-membership.fdmap-late`에서 late-window `fd-snapshot.json`과 `sudo-perf-record-fdmap.script.txt`를 actual로 함께 수집했다.
- checker `check_fd_snapshot_maps_overlap_and_payload_fds.py` 결과:
  - overlap threads:
    - `tid=344830`: `epfd=181 -> anon_inode:[eventpoll]`, `read_fd=182 -> anon_inode:[eventfd]`, `read_fd=192 -> null`
    - `tid=344838`: `epfd=183 -> anon_inode:[eventpoll]`, `read_fd=184 -> anon_inode:[eventfd]`, `read_fd=192 -> null`
    - `tid=344842`: `epfd=185 -> anon_inode:[eventpoll]`, `read_fd=186 -> anon_inode:[eventfd]`, `read_fd=192 -> null`
  - read-only threads는 payload fds `192/193/194`를 읽지만 snapshot 시점 target은 전부 `null`
  - checker result `fd_snapshot_did_not_cleanly_map_epoll_and_payload_roles`
- 의미:
  - late-window selector threads의 `epfd`와 control read fd(`eventfd`)는 clean하게 매핑됐다.
  - 하지만 payload socket fd `192/193/194`는 snapshot 시점에 이미 사라져 socket target을 잃었다.
  - 따라서 다음 직접 질문은 tighter or repeated FD snapshot으로 payload socket FD를 살아 있을 때 잡는 것이다.

2026-05-07 repeated FD snapshot payload socket update

- collector `run_probe_with_repeated_fd_snapshots.py`로 fresh run `/tmp/java-rust-mixed-membership.fdmap-repeat`에서 `snapshot_interval_ms=100`으로 149개 repeated snapshot과 late-window perf record를 actual로 함께 수집했다.
- checker `check_repeated_fd_snapshots_capture_payload_socket_targets.py` 결과:
  - payload fds:
    - `fd=192 count=164`
    - `fd=193 count=140`
    - `fd=194 count=5`
  - repeated snapshots는 `fd=192`를 여러 시점에서 실제 socket target으로 붙잡았다:
    - `socket:[52628630]`
    - `socket:[52628957]`
    - `socket:[52629902]`
    - `socket:[52630058]`
    - `socket:[52631835]`
    - `socket:[52630426]`
    - `socket:[52632781]`
    - `socket:[52633887]`
  - checker result `repeated_fd_snapshots_captured_live_socket_targets_for_payload_fds`
- 의미:
  - payload read fd를 살아 있을 때 실제 socket inode로 고정하는 데는 성공했다.
  - 다음 직접 질문은 이 `socket:[inode]`를 `/proc/net/tcp` 수준의 4-tuple(local/remote port)로 복구해 steelsearch transport capture의 starvation same socket port와 실제로 맞대는 것이다.

2026-05-07 repeated ss snapshot 4-tuple recovery update

- `/proc/net/tcp` parser path가 current artifact와 잘 안 맞아 equivalent path로 collector `run_probe_with_repeated_fd_and_ss_snapshots.py`를 추가하고 repeated `sudo ss -tanp` snapshot을 actual로 함께 수집했다.
- checker `check_ss_snapshots_map_payload_fds_to_ports.py` 결과:
  - payload fds:
    - `fd=193 count=160`
    - `fd=191 count=147`
    - `fd=194 count=6`
  - `fd=191` live tuple family 복구:
    - `peer_port=50713`
    - `local_ports={41488,41492,41500,41502,41518,33264,33270,33272}`
  - 이 local port set은 steelsearch transport capture peer ports와 실제 overlap
  - checker result `ss_snapshots_mapped_payload_fds_to_live_port_tuples_and_overlap_capture_peer_ports`
- 의미:
  - payload fd family를 actual starvation same-socket port set과 4-tuple 수준으로 연결하는 데 성공했다.
  - 따라서 다음 직접 질문은 `fd=191` live tuple family가 overlap threads의 occasional payload read인지, 아니면 read-only threads의 main payload path인지다.

2026-05-07 fd191 thread distribution update

- checker `check_fd191_thread_distribution.py`로 `/tmp/java-rust-mixed-membership.fd-ss-repeat/opensearch/sudo-perf-record-fd-ss.script.txt`의 `fd=191` read 분포를 actual로 집계했다.
- 결과:
  - overlap threads:
    - `tid=347658 fd191_reads=2 epoll_pwait=25`
    - `tid=347669 fd191_reads=3 epoll_pwait=34`
    - `tid=347673 fd191_reads=2 epoll_pwait=23`
    - 합계 `7`
  - read-only threads:
    - `tid=347662 fd191_reads=38`
    - `tid=347666 fd191_reads=35`
    - `tid=347667 fd191_reads=31`
    - `tid=347668 fd191_reads=36`
    - 합계 `140`
  - checker result `fd191_payload_path_is_mainly_read_only_thread_path_with_only_occasional_overlap_thread_reads`
- 의미:
  - starvation same-socket payload read의 main path는 overlap thread occasional read가 아니라 read-only threads 쪽이다.
  - 따라서 다음 직접 질문은 이 read-only payload threads가 JVM/Netty 안에서 정확히 어떤 role인지, 그리고 왜 payload read까지는 했는데 same-socket Netty `channelRead` marker로는 안 올라오는지다.

2026-05-07 payload read stack role update

- collector `run_probe_with_late_payload_read_stacks.py`로 fresh run `/tmp/java-rust-mixed-membership.read-stack-late`에서 late-window `perf record -g` read stack artifact를 actual로 수집했다.
- checker `check_payload_read_stack_role.py` 결과:
  - `payload_event_count=305`
  - main payload tids:
    - `349251 count=97`
    - `349247 count=74`
    - `349252 count=65`
    - `349253 count=61`
  - top stack symbols:
    - `read+0x6c`
    - `Java_sun_nio_ch_UnixFileDispatcherImpl_read0+0x34`
    - `JavaCalls::call_helper`
    - `JavaThread::thread_main_inner`
    - `thread_native_entry`
  - checker result `payload_read_only_path_reaches_jdk_nio_unixfiledispatcher_read0_before_any_higher_netty_marker`
- 의미:
  - main payload read-only path는 same-socket Netty `channelRead` marker보다 아래의 JDK NIO `read0`까지는 실제로 도달한다.
  - 따라서 다음 직접 질문은 이 OS tids를 Java thread name/role로 매핑해 exact JVM/Netty role을 고정하는 것이다.

2026-05-06 rust-primary/java-replica formed-handoff helper gap update

- `retry_probe_until_initializer_stage.py --stop-at formed_membership` 경로는 원래
  - known-good `STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS=5000`를 top-level env에만 두고
  - `probe_java_rust_mixed_membership.sh`가 이를 steelsearch launch env로 전달하지 못했으며
  - outer timeout도 internal probe budget보다 짧아 `report.json` 없이 먼저 잘릴 수 있었다.
- 이번 회차에서
  - `probe_java_rust_mixed_membership.sh`가 `JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS -> STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS` pass-through를 하도록 수정했고
  - `retry_probe_until_initializer_stage.py`는 namespaced env 사용 + `formed_membership`일 때 outer timeout 최소 `420s` 보장을 추가했다.
- 그 뒤 fresh probe `/tmp/java-rust-mixed-membership.lZr7jd/report.json` actual 결과는 여전히
  - `membership_formed=false`
  - `failure_stage=membership_timeout`
  - `observed_node_count=0`
- 의미:
  - current rust-primary/java-replica blocker는 helper wiring bug만으로 설명되지 않는다.
  - formed artifact `/tmp/java-rust-mixed-membership.QxL2L7/report.json`와 current failed artifact `/tmp/java-rust-mixed-membership.lZr7jd/report.json` actual compare에서는
    - formed run: `steelsearch_transport_follow_up_observed=true`
    - failed run: `steelsearch_transport_follow_up_observed=false`
    - formed run action set: `internal:transport/handshake`, `internal:discovery/request_peers`, `internal:cluster/request_pre_vote`, `internal:cluster/coordination/start_join`, `internal:cluster/coordination/publish_state`, `internal:coordination/fault_detection/follower_check`
    - failed run action set: `internal:tcp/handshake` only
  - 추가 persisted-state compare에서는
    - `initial_cluster_manager_nodes`
    - marker subset(`steelsearch_transport_follow_up_observed` 제외)
    - normalized seed peer identity
    - normalized bootstrap remote nodes
    - normalized membership members
    가 formed/failed 두 run에서 모두 동일했다.
  - visible start-command compare에서도 formed workdir `/tmp/java-rust-mixed-membership.3aSgG8`와 failed workdir `/tmp/java-rust-mixed-membership.lZr7jd`의 `opensearch/start-command.txt`, `steelsearch/start-command.txt`를 port만 정규화하면 shape가 완전히 동일했다.
  - probe는 이제 `opensearch/launch-env.json`, `steelsearch/launch-env.json`을 actual artifact로 남기며, fresh baseline `/tmp/java-rust-mixed-membership.envsnap.formed/report.json`에서
    - `STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS=5000`
    - `STEELSEARCH_INTEROP_SEED_PEER_IDENTITY_MANIFEST=...`
    같은 command에 남지 않는 env 값이 실제 snapshot에 기록됐다.
  - 다만 current tree fresh baseline itself도 overlay 없이 `membership_formed=false`, `failure_stage=membership_timeout`으로 닫혔다.
  - checker `check_old_formed_baseline_vs_current_tree.py` 결과
    - old formed artifact `/tmp/java-rust-mixed-membership.3aSgG8/report.json`는 `membership_formed=true`, `follow_up_observed=true`
    - current tree fresh baseline `/tmp/java-rust-mixed-membership.envsnap.formed/report.json`와 current tree fresh overlay failure `/tmp/java-rust-mixed-membership.lZr7jd/report.json`는 둘 다 `membership_formed=false`, `failure_stage=membership_timeout`, `follow_up_observed=false`
    이다.
  - 따라서 old formed artifact는 current tree가 fresh formed membership를 재현하지 못하는 동안 primary compare baseline으로 쓰기 안전하지 않다.
  - 추가로 `TransportHandshaker` timeout grace, `TcpTransport` handshake-timeout override, delayed `closeAndFail` 같은 experimental OpenSearch-side workaround를 원래 semantics로 되돌리고 `:server:compileJava` 후 fresh baseline `/tmp/java-rust-mixed-membership.envsnap.formed.recovered/report.json`를 다시 돌려도 결과는 여전히
    - `membership_formed=false`
    - `failure_stage=membership_timeout`
    - `steelsearch_transport_follow_up_observed=false`
    였다.
  - 따라서 current baseline regression은 최근 experimental timeout/close-grace branch만으로는 설명되지 않는다.
  - 또한 checker `check_current_baseline_vs_overlay_same_failure.py` 기준 current no-overlay baseline `/tmp/java-rust-mixed-membership.envsnap.formed.recovered/report.json`와 current overlay failure `/tmp/java-rust-mixed-membership.lZr7jd/report.json`는
    - 둘 다 `membership_formed=false`
    - 둘 다 `failure_stage=membership_timeout`
    - 둘 다 `follow_up_observed=false`
    - 둘 다 action set `{None: 1, internal:tcp/handshake: 10}`
    로 동일했다.
  - 따라서 current baseline regression은 overlay instrumentation 특이점으로 보기도 어렵다.
  - 추가로 checker `check_old_formed_vs_current_baseline_points_to_rust_runtime.py` 결과
    - old formed artifact `/tmp/java-rust-mixed-membership.3aSgG8/report.json`는 `follow_up_observed=true`, late-action count `9`
    - current no-overlay baseline `/tmp/java-rust-mixed-membership.envsnap.formed.recovered/report.json`는 `follow_up_observed=false`, late-action count `0`, action set `{None: 1, internal:tcp/handshake: 10}`
    이다.
  - 따라서 remaining regression candidate는 Java launch/overlay보다 current Rust post-`tcp/handshake` runtime branch 쪽이다.
  - checker `check_current_baseline_stops_before_followup_handler.py` 기준 current source에는 `internal:transport/handshake`, `request_peers`, `request_pre_vote`, `start_join`, `publish_state` follow-up branches가 여전히 모두 존재한다.
  - old formed artifact에서는 `follow_up_frame=2`, `post_follow_up_frame=3`, `handled_follow_up_request=3`까지 열렸지만, current baseline은 `follow_up_frame=0`, `post_follow_up_frame=0`, `idle_timeout=9`, `proactive_keepalive_total=9`로 끝난다.
  - 따라서 current regression boundary는 missing follow-up handler implementation이 아니라 follow-up frame arrival/dispatch 이전이다.
  - 추가로 current fresh overlay run `/tmp/java-rust-mixed-membership.4rOcYT`에서 checker `check_followup_absence_points_to_java_not_observing_low_level_response.py` 결과
    - Java side는 `before_send_request=110`
    - `send_request_meta_tcp_handshake=110`
    - `send_request_meta_transport_handshake=0`
    - `response_read=0`
    - `execute_handshake_listener_onResponse=0`
    - Rust capture action set `{None, internal:tcp/handshake}`
    였다.
  - 따라서 follow-up 부재의 직접 이유는 “peer가 follow-up을 보내기로 결정하지 않는다”라기보다 “Java peer가 low-level tcp handshake response를 관측하지 못해 high-level follow-up을 아예 보내지 못한다”는 쪽이다.
  - 따라서 다음 질문은 “무슨 input/runtime 차이가 current run을 tcp-handshake-only에 묶고 formed run은 follow-up actions로 승격시키는가”다.

2026-05-05 low-level tcp handshake response dispatch question

- fresh probe `/tmp/java-rust-mixed-membership.K6mkXU`에서는
  - `before_send_request=37`
  - `after_send_request=37`
  - `response_read=0`
  - `handle_response=0`
  - `handle_exception=0`
  - `handle_local_exception=0`
  - `remove_handler=73`
  - `handshake_timeout=36`
- 의미:
  - Java low-level tcp handshake는 send까지는 가지만 response parser/handler callback은 한 번도 열리지 않음
  - 다음 질문은 Rust response가 Java inbound decoder/response dispatch까지 실제로 들어오는지, 아니면 wire 상에서 drop/close되는지임
  - 추가로 `remove_handler`가 timeout count보다 많은 이유가 close-listener 중복 제거인지도 아직 명확하지 않음

2026-05-05 native message handler boundary update

- fresh probe `/tmp/java-rust-mixed-membership.xQ8Xbg`에서는
  - `before_send_request=37`
  - `after_send_request=37`
  - `steelsearch_native_message_stage=handshake_response_* = 0`
  - `response_read=0`
  - `handle_response=0`
  - `handshake_timeout=36`
- 의미:
  - low-level tcp handshake response는 Java `NativeMessageHandler` handshake-response branch에도 도달하지 않음
  - 다음 질문은 response bytes가 `Netty4MessageChannelHandler`/`InboundPipeline` decoder까지는 들어오는지, 아니면 그 이전 channel/wire 경계에서 소실되는지임

2026-05-05 decoder boundary update

- fresh probe `/tmp/java-rust-mixed-membership.jtsvtA`에서는
  - `send_port=39691`
  - `before_send_request=37`
  - `handshake_timeout=36`
  - `channel_read_total=1`
  - `handle_bytes_total=1`
  - `channel_read_for_send_port=0`
  - `handle_bytes_for_send_port=0`
  - `native_handshake_response_header=0`
- 의미:
  - current sample에서 Java discovery가 연결한 rust transport port 기준으로는 inbound bytes가 `Netty4MessageChannelHandler`/`InboundPipeline`에 들어오지 않음
  - 따라서 다음 질문은 Rust가 low-level tcp handshake response bytes를 실제로 write/flush하는지, 아니면 response 전에 remote EOF/close로 끝나는지임

2026-05-05 rust outbound response boundary update

- fresh probe `/tmp/java-rust-mixed-membership.JE5h6i`에서는 rust `internal:tcp/handshake` response branch marker가
  - `before_write=37`
  - `after_write=37`
  - `after_flush=37`
  - `no_follow_up_within_400ms=36`
  - `follow_up_received=0`
- 의미:
  - Rust는 low-level tcp handshake response bytes를 실제로 write/flush함
  - immediate remote EOF/close 전에 실패하는 문제는 아님
  - 따라서 다음 질문은 Rust response bytes shape/serialization이 Java `TcpTransport.executeHandshake` parser expectation과 truly compatible한지임

2026-05-05 raw response shape update

- same workdir `/tmp/java-rust-mixed-membership.JE5h6i`에서
  - local accepted probe response body hex:
    - `00000000000000010908216b1300000002000093b1bb41`
  - discovery capture response frame body prefix hex:
    - `00000000000000010908216b1300000002000093b1bb41`
- 의미:
  - Rust low-level tcp handshake response bytes shape는 same workdir local accepted probe와 정확히 일치함
  - 따라서 current blocker는 raw response serialization mismatch가 아니라 discovery socket/channel association 또는 lifecycle mismatch 쪽이다

2026-05-04 explicit export rebuild benchmark update

- 3회 tiny-leaf benchmark에서 보였던 `77ms` explicit win은 9회 larger-sample rerun에서 재현되지 않았음
- latest actual result:
  - `star median = 3594ms`
  - `explicit median = 3607ms`
  - `mean delta = +1.11ms`
- 의미:
  - current evidence로는 explicit export patch를 stable rebuild speedup으로 주장하기 어려움
  - 다음 질문은 earlier 3회 결과가 sample-order/cache artifact였는지임

- order-sensitivity rerun 결과:
  - `star -> explicit`: explicit median이 `-27ms`
  - `explicit -> star`: star median이 `-34ms`
- 의미:
  - mode와 무관하게 두 번째로 측정된 쪽이 더 빨라짐
  - 따라서 earlier `77ms` win은 explicit export patch 효과보다 second-run cache/order artifact일 가능성이 더 큼

- stable `cargo --timings` first/second incremental 비교 결과:
  - explicit mode:
    - `lib_duration +60ms`
    - `rmeta +60ms`
    - `post-rmeta +0ms`
  - star mode:
    - `lib_duration +70ms`
    - `rmeta +20ms`
    - `post-rmeta +50ms`
- 의미:
  - wall-clock benchmark에서는 second run이 더 빨랐지만, stable timings section에서는 second run이 오히려 약간 느리게 나옴
  - 따라서 현재 남은 질문은 wall-clock advantage와 stable timings section 간 불일치임

- plain vs `--timings` wall-clock pair 비교:
  - explicit mode:
    - plain `delta_second_minus_first = +30ms`
    - timings `delta_second_minus_first = -39ms`
  - star mode:
    - plain `delta_second_minus_first = -56ms`
    - timings `delta_second_minus_first = -82ms`
- 의미:
  - `--timings` 계측 자체가 유일한 설명은 아님
  - 현재 first/second sign 자체가 pair-level noise를 크게 타므로, 다음은 larger paired sample로 sign stability를 보는 쪽이 맞음

- 7회 paired sign stability 결과:
  - explicit mode:
    - plain `second_faster=5`, `second_slower=2`
    - timings `second_faster=5`, `second_slower=2`
  - star mode:
    - plain `second_faster=3`, `second_slower=4`
    - timings `second_faster=3`, `second_slower=4`
- 의미:
  - cross-mode stable second-run advantage는 성립하지 않음
  - 남은 질문은 explicit의 `5:2`와 star의 `3:4`가 실제 mode-specific bias인지, 아니면 여전히 noise인지임

- 15회 plain paired sample 확대 결과:
  - explicit:
    - `second_faster=7`, `second_slower=8`
    - `share=0.467`
    - `two_sided_binomial_p=1.0`
  - star:
    - `second_faster=9`, `second_slower=6`
    - `share=0.6`
    - `two_sided_binomial_p=0.607239`
- 의미:
  - 둘 다 `50/50`에서 유의하게 벗어나지 않음
  - 따라서 `explicit 5:2 vs star 3:4` 차이는 mode-specific bias보다 추가 noise로 보는 편이 더 맞음
  - 다음 질문은 `-73ms..+146ms`급 pair variance의 직접 원인이 cargo 내부인지 외부 scheduler/IO jitter인지임

- `--timings` pair origin 비교 결과:
  - explicit:
    - `wall/lib sign match = 5/7`
    - `wall_delta_stddev = 43.58ms`
    - `os_node_lib_delta_stddev = 52.33ms`
    - `residual_delta_stddev = 31.57ms`
  - star:
    - `wall/lib sign match = 7/7`
    - `wall_delta_stddev = 105.27ms`
    - `os_node_lib_delta_stddev = 133.39ms`
    - `residual_delta_stddev = 37.73ms`
- 의미:
  - current pair variance는 외부 scheduler/IO jitter보다 cargo 내부 `os_node` lib compile variance 쪽이 더 가깝다
  - 다음 질문은 이 lib variance가 `rmeta`와 `post-rmeta` 중 어디서 더 크게 오는지임

- `os_node` lib variance split 결과:
  - explicit:
    - `rmeta_stddev = 31.56ms`
    - `post_rmeta_stddev = 38.33ms`
  - star:
    - `rmeta_stddev = 22.59ms`
    - `post_rmeta_stddev = 25.87ms`
- 의미:
  - 두 mode 모두 `post-rmeta` 쪽이 `rmeta`보다 약간 더 크게 흔들림
  - 따라서 current pair variance는 pure metadata jitter보다 codegen/link를 포함한 post-rmeta variance 쪽이 더 가깝다
  - 다음 질문은 post-rmeta 안에서 rustc codegen / LLVM / link 중 어디가 더 흔들리느냐임

- nightly `-Z time-passes` 5회 반복 결과 (`os-node --lib`):
  - `LLVM_passes stddev = 1.17ms`
  - `link stddev = 0.89ms`
  - `link_rlib stddev = 0.75ms`
  - `codegen_crate stddev = 0.49ms`
  - `codegen_to_LLVM_IR`는 incremental path에서 관측되지 않음
- 의미:
  - post-rmeta 내부에서 가장 흔들리는 phase는 `LLVM_passes`
  - 하지만 절대 규모가 매우 작아서 stable `post-rmeta stddev 25~38ms`를 그대로 설명하지는 못함
  - 다음 질문은 nightly tiny phase variance와 stable post-rmeta delta 사이의 measurement mismatch임

- stable `cargo --timings` quantization 확인:
  - explicit / star 모두에서
    - `duration_ms`
    - `rmeta_ms`
    - `post_rmeta_ms`
    가 전부 `10ms` 배수로만 기록됨
- 의미:
  - stable `post-rmeta`는 fine-grained phase timer가 아니라 `10ms-grid aggregate residual`
  - 따라서 nightly `time-passes`의 ~1ms-scale phase variance와 stable `post-rmeta stddev 25~38ms`는 동일 정밀도의 직접 비교 대상이 아님
  - 다음 질문은 stable `post-rmeta`가 어떤 coarse aggregate semantics 때문에 이런 residual variance로 보이는지임

- stable UNIT_DATA schema 확인:
  - `os_node_lib_unit_keys = ["duration", "i", "mode", "name", "rmeta_time", "start", "target", "unlocked_rmeta_units", "unlocked_units", "version"]`
  - `post_rmeta` native field는 없음
  - current `post_rmeta_ms`는 `duration_ms - rmeta_ms`로 계산한 값
- 의미:
  - stable `post-rmeta`는 raw phase가 아니라 derived residual
  - 남은 질문은 이 residual이 pure self-time인지, 아니면 unlock/wait semantics까지 섞인 aggregate인지임

- actual UNIT_DATA overlap 확인:
  - `os_node_lib_start_ms = 50`
  - `os_node_lib_rmeta_ready_ms = 1920`
  - `os_node_lib_finish_ms = 2320`
  - `unlocked_rmeta_units = []`
  - `unlocked_units = [os-node bin "steelsearch" @ 2320ms]`
- 의미:
  - current build에서는 downstream `steelsearch`가 `rmeta_ready` 직후가 아니라 `lib finish` 시점에 시작함
  - 따라서 current `post-rmeta` residual은 rmeta-unlock overlap보다 full-unit completion/unlock tail 쪽으로 읽는 편이 맞음
  - 다음 질문은 `rmeta_time` field가 있음에도 왜 current build graph에서 `unlocked_rmeta_units`가 비는지임

- verbose rustc invocation 확인:
  - `steelsearch` bin rustc는 `--extern os_node=.../libos_node-....rlib`
  - `.rmeta` consumer가 아님
- 의미:
  - current build graph에서 `unlocked_rmeta_units=[]`인 직접 원인은 downstream `steelsearch`가 metadata-only consumer가 아니라 full `rlib` consumer라는 점
  - 다음 질문은 `cargo check`류 graph에서는 실제 `rmeta` consumer가 생기는지임

- `cargo check --timings` graph 확인:
  - `os_node_lib_rmeta_ready_ms = 1320`
  - `os_node_lib_finish_ms = 1440`
  - `unlocked_rmeta_units = []`
  - `unlocked_units = [os-node bin "steelsearch" (check) @ 1440ms]`
- 의미:
  - current repo의 `cargo build`뿐 아니라 `cargo check` graph에서도 downstream `steelsearch`는 rmeta consumer가 아님
  - 따라서 다음 질문은 current graph에 rmeta consumer가 없어도 `rmeta_time` field가 schema상 항상 기록되는지임

- build/check 전체 unit 집계:
  - build:
    - `unit_count = 2`
    - `rmeta_time_present_count = 2`
    - `rmeta_time_nonnull_count = 1`
    - `unlocked_rmeta_nonempty_count = 0`
  - check:
    - `unit_count = 2`
    - `rmeta_time_present_count = 2`
    - `rmeta_time_nonnull_count = 2`
    - `unlocked_rmeta_nonempty_count = 0`
- 의미:
  - current graph에서는 `rmeta` consumer edge가 없어도 `rmeta_time` field 자체는 schema상 계속 존재함
  - 특히 `bin "steelsearch" (check)`도 `rmeta_time_ms=110`을 가지므로, 이 field는 unlock edge 자체보다 더 일반적인 internal milestone일 가능성이 큼

- build/check `steelsearch` rustc emit 비교:
  - build:
    - `--emit=dep-info,link`
    - `build_has_metadata_emit = false`
  - check:
    - `--emit=dep-info,metadata`
    - `check_has_metadata_emit = true`
- 의미:
  - `bin "steelsearch" (check)`의 `rmeta_time_ms=110`은 unlock edge보다 metadata emit milestone으로 읽는 편이 더 맞다
  - 다음 질문은 current graph 전체에서 `rmeta_time nonnull <=> emit includes metadata`가 일관되는지임

- current build/check graph 전체 매칭:
  - build lib: `emit=dep-info,metadata,link`, `rmeta_time_nonnull=true`
  - build bin: `emit=dep-info,link`, `rmeta_time_nonnull=false`
  - check lib: `emit=dep-info,metadata`, `rmeta_time_nonnull=true`
  - check bin: `emit=dep-info,metadata`, `rmeta_time_nonnull=true`
  - `all_units_equivalent = true`
- 의미:
  - current graph의 4개 unit에서는 `rmeta_time nonnull <=> emit includes metadata`가 모두 성립함
  - 다음 질문은 더 넓은 `cargo test --no-run` graph에서도 metadata-only consumer나 `unlocked_rmeta_units`가 실제로 생기는지임

- `cargo test --no-run --test dev_cluster_daemons` graph 확인:
  - `os_node_lib_rmeta_ready_ms = 1940`
  - `os_node_lib_finish_ms = 2350`
  - `unlocked_rmeta_units = []`
  - `unlocked_units = [bin "steelsearch" @ 2350ms, test "dev_cluster_daemons" (test) @ 2350ms]`
- 의미:
  - current repo에서 확인한 build/check/test graph는 모두 metadata-only consumer를 만들지 않음
  - 다음 질문은 workspace 범위에서 실제 `unlocked_rmeta_units`를 만드는 다른 target graph가 있는지임

- `cargo check --workspace --timings` 스캔:
  - `unit_count = 3`
  - `unlocked_rmeta_nonempty_count = 0`
  - `unlocked_rmeta_examples = []`
- 의미:
  - current repo에서 확인한 narrow graph뿐 아니라 workspace check graph에서도 metadata-only consumer가 관측되지 않음
  - 다음 질문은 `--all-targets`나 다른 cargo invocation에서라도 실제 `unlocked_rmeta_units`가 생기는지임

- `cargo check --all-targets --timings -p os-node` 스캔:
  - `unit_count = 6`
  - `unlocked_rmeta_nonempty_count = 0`
  - `unlocked_rmeta_examples = []`
- 의미:
  - current repo에서 확인한 build/check/test/workspace-check/all-targets graph는 모두 metadata-only consumer를 만들지 않음
  - 다음 질문은 workspace-wide `cargo test --no-run` graph에서도 같은지임

- `cargo test --workspace --no-run --timings` 스캔:
  - `unit_count = 7`
  - `unlocked_rmeta_nonempty_count = 0`
  - `unlocked_rmeta_examples = []`
- 의미:
  - current repo에서 확인한 representative cargo invocation들은 모두 metadata-only consumer를 만들지 않음
  - 다음 질문은 current repo 밖 minimal fixture를 만들어 `unlocked_rmeta_units` path 자체를 재현해야 하는지임

- minimal external fixture 확인:
  - fixture: `producer` lib + `consumer` bin
  - `cargo check --timings --workspace`
  - `producer` unit:
    - `unlocked_rmeta_units = []`
    - `unlocked_units = [consumer]`
- 의미:
  - current observation은 repo-local 구조가 아니라 current Cargo 1.76 timing html behavior 쪽일 가능성이 더 큼
  - 다음 질문은 Cargo timing html/source 기준으로 `unlocked_rmeta_units`가 어떤 조건에서만 채워지는지임

- 목적:
  - `Java primary <-> Rust replica actual run evidence 수집`의 success path를 실제 mixed cluster에서 실행
- 해결된 전제:
  - `tools/run-opensearch-dev.sh`는 install tree distro를 우선 사용하도록 바꿔서 Java/OpenSearch node 자체는 기동 가능해짐
- 현재 확인된 blocker:
  - OpenSearch node는 실제로 기동되지만, Steelsearch dev daemon이 여전히 standalone-only 모드로 올라와 Java cluster membership에 참여하지 않음
  - 실제 stdout marker:
    - `development mode: standalone HTTP compatibility surface only; development_security=disabled, production security and multi-node runtime are not complete`
  - 결과:
    - OpenSearch `_cat/nodes`에서 2-node mixed membership이 형성되지 않음
- 의미:
  - Java node provisioning 문제는 해소됐지만, Rust daemon bootstrap이 mixed Java same-cluster participation 경로를 아직 열지 못함
  - success path / negative path actual artifact 수집은 2-node mixed membership 형성 전까지 진행 불가
- 필요한 결정:
  - Steelsearch side에 standalone-only가 아닌 mixed-cluster participation bootstrap 경로가 이미 있는지
  - 없다면 별도 bootstrap/feature flag를 추가할지

- probe 개선 후 추가로 확인된 사실:
  - `probe_java_rust_mixed_membership.sh`는 이제 실패 시에도 `report.json`을 남김
  - short timeout smoke에서는 `blocker_class=opensearch_startup_timeout`이 실제로 기록됨
  - `STEELSEARCH_MODE=production` + `STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED=true`로 probe를 돌리면 Java node는 뜨지만 mixed membership은 형성되지 않고 `blocker_class=production_mode_blocked`가 기록됨
  - 즉 production flag는 same-cluster participation을 여는 경로가 아니라 `validate_production_mode_request(...)` hard block에 걸리는 경로임
  - default development path는 짧은 membership timeout에서는 `membership_timeout`으로 끝나므로, 기존에 관측했던 `standalone HTTP compatibility surface only` marker까지 fully boot되는 장시간 probe artifact를 별도로 다시 수집해야 함

- 장시간 development probe 실제 artifact:
  - work dir: `/tmp/probe-fast-standalone.wqEuhA`
  - `observed_node_count = 1`
  - `membership_formed = false`
  - `failure_stage = membership_timeout`
  - `blocker_class = standalone_only_bootstrap`
  - `markers.steelsearch_standalone_only = true`
  - 즉 기본 development bootstrap은 fully boot 후에도 same-cluster membership으로 전환되지 않고 standalone-only surface에 머뭄

- same-cluster intent fail-closed gate 추가 후 확인:
  - `java_write_forwarding_validated + remote discovery.seed_hosts` 조합은 더 이상 standalone-only fallback으로 조용히 기동되지 않음
  - unit test: `daemon_config_rejects_java_same_cluster_intent_without_native_transport_join` 통과
  - actual probe artifact: `/tmp/probe-samecluster-block.MuJHQi/report.json`
    - `observed_node_count = 1`
    - `membership_formed = false`
    - `blocker_class = same_cluster_participation_unimplemented`
    - `markers.steelsearch_same_cluster_participation_unimplemented = true`
  - 남은 구현은 fallback 차단이 아니라 실제 native transport join participation path 자체임

- Java transport seed passive probe 결과:
  - artifact: `/tmp/transport-probe-os/transport-seed-report.json`
  - `tcp_connected = true`
  - `peer_speaks_first = false`
  - `peer_closed_immediately = false`
  - 의미: Java/OpenSearch transport port는 수동 대기 상태이며, Steelsearch 쪽에서 먼저 native transport handshake preamble을 보내야 함

- Java transport handshake preamble spec artifact:
  - artifact: `/tmp/opensearch-transport-handshake-spec.json`
  - `marker_prefix = ES`
  - `bytes_required_for_message_size = 6`
  - `tcp_handshake_action = internal:tcp/handshake`
  - `transport_identity_handshake_action = internal:transport/handshake`
  - `server_validates_prefix = true`
  - 의미: 다음 구현은 passive probe가 아니라 이 spec대로 client-initiated transport handshake request를 실제로 보내는 단계임

- Java transport handshake actual transmission artifact:
  - artifact: `/tmp/transport-handshake-os/tcp-handshake-probe.json`
  - `request_sent = true`
  - `tcp_connected = true`
  - `response_received = false`
  - Java server log: `UnsupportedVersionException: Unsupported version [ES 3.7.0]`
  - 의미: request frame은 transport decoder까지 도달했지만, header/version/status encoding이 OpenSearch acceptance와 아직 맞지 않음

- Java reference frame replay 결과:
  - reference frame dump: `tools/dump_java_tcp_handshake_frame.sh`
  - accepted response artifact: `/tmp/transport-java-frame-os/java-reference-handshake-report.json`
  - `request_frame_source = frame_hex`
  - `response_received = true`
  - `response_starts_with_es = true`
  - 의미: header/version/status alignment 자체는 해결됐고, 다음 남은 일은 response body를 decode해서 peer identity discovery로 올리는 단계임

- accepted tcp handshake response parser 결과:
  - artifact: `/tmp/transport-java-frame-os/tcp-handshake-response-parsed.json`
  - `is_response = true`
  - `is_handshake = true`
  - `peer_identity_present = false`
  - `remaining_bytes_after_version = ""`
  - 의미: `internal:tcp/handshake` accepted response는 version-only에 가깝고, peer identity는 별도 `internal:transport/handshake` 단계에서 얻어야 함

- `internal:transport/handshake` peer identity discovery 결과:
  - request frame dump:
    - `tools/dump_java_transport_handshake_frame.sh`
  - full response artifact:
    - `/tmp/transport-identity-os/transport-handshake-report.json`
  - parsed response artifact:
    - `/tmp/transport-identity-os/transport-handshake-response-parsed.json`
  - 실제 파싱 결과:
    - `peer_identity_present = true`
    - `cluster_name = os-transport-id`
    - `discovery_node.name = os-transport-id-1`
    - `discovery_node.transport_address = 127.0.0.1:45321`
    - `discovery_node.roles = [cluster_manager, data, ingest, remote_cluster_client]`
  - 의미:
    - Java/OpenSearch peer identity discovery에 필요한 request/response wire는 확보됨
    - 남은 blocker는 handshake discovery 자체가 아니라, 이 정보를 Steelsearch daemon bootstrap/native transport join path에 실제 연결해 same-cluster membership으로 전환하는 일임

- mixed membership probe에 actual seed peer identity를 연결한 결과:
  - artifact:
    - `/tmp/java-rust-mixed-membership.lQCar5/report.json`
  - 현재 report에는 `seed_peer_identity`가 실제로 포함됨:
    - `cluster_name = mixed-java-rust-dev`
    - `discovery_node.name = java-primary-1`
    - `discovery_node.transport_address = 127.0.0.1:55313`
    - `roles = [cluster_manager, data, ingest, remote_cluster_client]`
  - 동시에 결과는 여전히:
    - `membership_formed = false`
    - `blocker_class = standalone_only_bootstrap`
    - `markers.steelsearch_standalone_only = true`
  - 의미:
    - Java seed peer identity discovery는 mixed-membership probe 안에서 실제로 동작함
    - 남은 실제 blocker는 seed discovery가 아니라, discovered peer를 사용해 Steelsearch daemon이 standalone-only를 벗어나 native transport join/bootstrap으로 진입하지 못하는 점임

- same-cluster intent + actual seed identity manifest를 daemon bootstrap에 연결한 결과:
  - artifact:
    - `/tmp/java-rust-mixed-membership.O2RydJ/report.json`
  - 실제 관측:
    - `seed_peer_identity.peer_identity_present = true`
    - `markers.steelsearch_same_cluster_participation_unimplemented = false`
    - `markers.steelsearch_standalone_only = true`
    - `blocker_class = standalone_only_bootstrap`
  - 의미:
    - same-cluster intent가 더 이상 generic preflight blocker로 끝나지 않고, actual Java peer identity manifest를 받아 runtime startup까지 진행됨
    - 하지만 runtime은 여전히 standalone-only surface로 머무르므로, 남은 핵심 구현은 actual native transport join participation 자체임

- bootstrap gateway state가 actual Java peer identity를 반영하는지 재검증한 결과:
  - artifact:
    - `/tmp/java-rust-mixed-membership.0PZ9by/report.json`
  - 실제 관측:
    - `steelsearch_bootstrap_remote_nodes[0].node_id = Cm-KXHeGSf6Wv06KWYohCA`
    - `steelsearch_bootstrap_remote_nodes[0].transport_address = 127.0.0.1:37205`
    - `seed_peer_identity.discovery_node.id = Cm-KXHeGSf6Wv06KWYohCA`
    - `seed_peer_identity.discovery_node.transport_address = 127.0.0.1:37205`
    - `markers.steelsearch_bootstrap_uses_seed_peer_identity = true`
  - 동시에 결과는 여전히:
    - `membership_formed = false`
    - `blocker_class = standalone_only_bootstrap`
  - 의미:
    - bootstrap state에 actual Java peer identity가 반영되는 것까지는 완료
    - 남은 구현은 이 bootstrap state를 실제 native transport join / same-cluster participation으로 연결하는 단계임

- production membership manifest persist 결과:
  - artifact:
    - `/tmp/java-rust-mixed-membership.d6U0Fn/report.json`
    - `/tmp/java-rust-mixed-membership.d6U0Fn/steelsearch/data/production-membership.json`
  - 실제 관측:
    - `markers.steelsearch_membership_state_persisted = true`
    - `steelsearch_membership_members`에 2개 node 존재:
      - Java peer:
        - `node_id = _FoW7CoXRX6mn5YnJzyw7A`
        - `node_name = java-primary-1`
      - local Rust:
        - `node_id = rust-replica-1`
        - `node_name = rust-replica-1`
    - Java peer member identity는 `seed_peer_identity.discovery_node`와 일치
  - 의미:
    - same-cluster bootstrap state는 이제 gateway-state뿐 아니라 production-membership manifest에도 actual Java peer identity를 실제로 기록함
    - 남은 blocker는 artifact persistence가 아니라, 이 persisted membership/bootstrap state를 사용한 actual native transport join / OpenSearch-side 2-node membership 형성임

- Steelsearch transport seed listener bind 결과:
  - artifact:
    - `/tmp/java-rust-mixed-membership.6HERIg/report.json`
    - `/tmp/java-rust-mixed-membership.6HERIg/steelsearch/transport-connect.json`
  - 실제 관측:
    - `steelsearch_transport_probe.tcp_connected = true`
    - `markers.steelsearch_transport_accepting_connections = true`
    - 동시에:
      - `membership_formed = false`
      - `blocker_class = standalone_only_bootstrap`
  - 의미:
    - Steelsearch dev daemon은 이제 transport port를 실제로 bind하고 TCP accept까지 함
    - 남은 blocker는 “transport port가 안 열린다”가 아니라, 열린 listener가 OpenSearch native transport join protocol에 실제로 참여하지 않는 점임
2026-05-03 mixed Java actual run blocker update

- latest actual artifact:
  - `/tmp/java-rust-mixed-membership.IEbsal/report.json`
- confirmed:
  - Java seed peer identity discovery succeeds
  - Steelsearch bootstrap reflects actual Java peer identity
  - `production-membership.json` persists both Java and Rust members
  - Steelsearch transport port accepts TCP connections
  - Steelsearch transport listener now accepts Java reference `internal:tcp/handshake`
    - `steelsearch_transport_handshake_probe.response_received = true`
    - `steelsearch_transport_handshake_probe.response_starts_with_es = true`
- current blocker remains:
  - `membership_formed = false`
  - `blocker_class = standalone_only_bootstrap`
- interpretation:
  - remaining gap is no longer seed discovery or tcp handshake acceptance
  - remaining gap is that Steelsearch still does not participate in the next OpenSearch native transport discovery/join request flow after accepted `internal:tcp/handshake`

2026-05-03 passive inbound transport capture update

- latest actual artifact:
  - `/tmp/java-rust-mixed-membership.xfsmAw/report.json`
- probe mode:
  - `JAVA_RUST_MIXED_MEMBERSHIP_SKIP_ACTIVE_STEELSEARCH_PROBES=1`
- confirmed:
  - active self-probe를 끄면 `steelsearch_transport_probe`, `steelsearch_transport_handshake_probe`, `steelsearch_transport_capture`가 모두 비어 있음
  - 즉 current bootstrap 조건에서는 OpenSearch가 Steelsearch seed transport에 actual dial/handshake를 시도하지 않음
- current blocker interpretation:
  - 남은 1차 gap은 Steelsearch listener의 handshake 응답 자체가 아니라
  - OpenSearch discovery/bootstrap 조건이 Steelsearch seed transport dial을 트리거하지 않는 점
  - 따라서 `accepted internal:tcp/handshake 이후 request decode/response`보다 먼저 `why no inbound dial`을 규명해야 함

2026-05-03 bootstrap/discovery alignment update

- latest actual artifact:
  - `/tmp/java-rust-mixed-membership.xQwrVL/report.json`
- change:
  - same-cluster intent probe 기본값을 `cluster.initial_cluster_manager_nodes=java-primary-1,rust-replica-1`로 정렬
- confirmed:
  - OpenSearch가 이제 Steelsearch seed `127.0.0.1:41385`로 실제 dial함
  - Steelsearch transport capture에 반복 inbound exchange가 기록됨
  - each exchange:
    - first frame: `internal:tcp/handshake`
    - follow-up frame: `internal:transport/handshake`
  - OpenSearch stderr:
    - `handshake failed for [connectToRemoteMasterNode[127.0.0.1:41385]]`
    - `NodeDisconnectedException ... [internal:transport/handshake] disconnected`
- current blocker:
  - bootstrap/discovery 조건은 맞음
  - remaining gap is `internal:transport/handshake` response path on Steelsearch

2026-05-03 transport handshake response update

- latest actual artifacts:
  - `/tmp/java-rust-mixed-membership.gIXOQO/steelsearch/data/transport-seed-capture.json`
  - `/tmp/java-rust-mixed-membership.gIXOQO/opensearch/stdout.log`
- confirmed:
  - Steelsearch now responds to `internal:transport/handshake` with an OpenSearch-compatible node identity response
  - OpenSearch stdout now contains:
    - `completed handshake with [{rust-replica-1}{rust-replica-1}{rust-replica-1}{127.0.0.1}{127.0.0.1:37521}{dim}]`
  - transport capture still shows the inbound sequence:
    - first frame: `internal:tcp/handshake`
    - follow-up frame: `internal:transport/handshake`
- current blocker:
  - handshake itself is now accepted
  - remaining gap is the next followup connection/request after completed transport handshake
  - OpenSearch still reports:
    - `completed handshake ... but followup connection failed`

2026-05-03 followup channel failure update

- latest actual artifacts:
  - `/tmp/java-rust-mixed-membership.b849cl/steelsearch/data/transport-seed-capture.json`
  - `/tmp/java-rust-mixed-membership.b849cl/opensearch/stdout.log`
- confirmed:
  - transport listener waits longer after `internal:transport/handshake` response
  - latest capture still has:
    - `follow_up_frame.action_hint = internal:transport/handshake`
    - `post_follow_up_frame = null`
  - OpenSearch stdout now also reports:
    - `ConnectTransportException ... a channel closed while connecting`
- current blocker:
  - next gap is not handshake serialization anymore
  - next gap is keeping the post-handshake transport channel alive so OpenSearch can establish its followup connection before any discovery/join request decode can happen

2026-05-03 followup connection concurrency update

- latest actual artifact:
  - `/tmp/java-rust-mixed-membership.8kzznu/report.json`
- change:
  - Steelsearch transport seed listener now dispatches each accepted socket to its own worker thread instead of handling all inbound transport sockets sequentially
- confirmed:
  - `internal:transport/handshake` is no longer only a same-socket follow-up
  - actual capture now contains separate inbound sockets whose `first_frame.action_hint = internal:transport/handshake`
  - despite concurrent accept, the report is still:
    - `membership_formed = false`
    - `blocker_class = standalone_only_bootstrap`
  - OpenSearch stdout still repeats:
    - `completed handshake with [{rust-replica-1}...] but followup connection failed`
    - `NodeDisconnectedException ... [internal:transport/handshake] disconnected`
- interpretation:
  - the remaining blocker is not listener starvation or sequential accept backlog
  - the remaining gap is that Steelsearch accepts the separate followup socket but does not promote it into the persistent transport channel/profile OpenSearch expects after handshake

2026-05-03 discovery request followup update

- latest actual artifacts:
  - `/tmp/java-rust-mixed-membership.st2u2d/steelsearch/data/transport-seed-capture.json`
  - `/tmp/java-rust-mixed-membership.st2u2d/opensearch/stdout.log`
- change:
  - Steelsearch now returns the OpenSearch-compatible `internal:transport/handshake` identity response even when that handshake arrives as the first frame on a separate followup socket
- confirmed:
  - transport capture now includes actual inbound discovery traffic:
    - `first_frame.action_hint = internal:discovery/request_peers`
  - OpenSearch stdout now advances from pure handshake failure to:
    - `setting initial configuration to VotingConfiguration{...,rust-replica-1}`
    - `have discovered ... {rust-replica-1}{rust-replica-1}{rust-replica-1}{127.0.0.1}{127.0.0.1:56013}{dim} which is a quorum`
- current blocker:
  - membership is still not formed
  - but the blocker is no longer transport channel establishment
  - the next missing implementation is decoding and responding to `internal:discovery/request_peers`, then the subsequent join/election transport requests

2026-05-03 pre-vote request followup update

- latest actual artifacts:
  - `/tmp/java-rust-mixed-membership.R5q0R2/steelsearch/data/transport-seed-capture.json`
  - `/tmp/java-rust-mixed-membership.R5q0R2/opensearch/stdout.log`
- change:
  - Steelsearch now returns a minimal `PeersResponse(leader=None, knownPeers=[], term=0)` for `internal:discovery/request_peers`
- confirmed:
  - transport capture now advances beyond peer discovery to actual coordinator traffic:
    - `first_frame.action_hint = internal:cluster/request_pre_vote`
  - OpenSearch stdout reaches:
    - `setting initial configuration to VotingConfiguration{...,rust-replica-1}`
- current blocker:
  - membership is still not formed
  - the next missing implementation is decoding and responding to `internal:cluster/request_pre_vote`, then subsequent join/election requests

2026-05-03 start-join followup update

- latest actual artifacts:
  - `/tmp/java-rust-mixed-membership.vii1pq/steelsearch/data/transport-seed-capture.json`
  - `/tmp/java-rust-mixed-membership.vii1pq/opensearch/stdout.log`
- change:
  - Steelsearch now returns a minimal `PreVoteResponse(currentTerm=0, lastAcceptedTerm=0, lastAcceptedVersion=0)` for `internal:cluster/request_pre_vote`
- confirmed:
  - transport capture now advances to:
    - `first_frame.action_hint = internal:cluster/coordination/start_join`
  - OpenSearch stdout now contains a real join attempt:
    - `failed to join ... [internal:cluster/coordination/join]`
- current blocker:
  - membership is still not formed
  - the next missing implementation is decoding and responding to `internal:cluster/coordination/start_join`, then the subsequent join request path

2026-05-03 start-join response fix and publication-stage blocker update

- latest actual artifacts:
  - `/tmp/java-rust-mixed-membership.haJZ7G/report.json`
  - `/tmp/java-rust-mixed-membership.haJZ7G/steelsearch/data/transport-seed-capture.json`
  - `/tmp/java-rust-mixed-membership.haJZ7G/opensearch/stdout.log`
- change:
  - Steelsearch no longer returns a malformed `Join` as the direct `internal:cluster/coordination/start_join` response
  - it now returns `Empty` and sends an outbound `internal:cluster/coordination/join` request to the Java peer
- confirmed:
  - the previous `Failed to deserialize response ... Message not fully read` error is gone
  - OpenSearch now reaches real election/publication progress:
    - `elected-as-cluster-manager ([2] nodes joined)`
  - transport capture advances beyond `start_join` into publication-stage traffic:
    - `first_frame.action_hint = internal:coordination/fault_detection/follower_check`
    - `first_frame.action_hint = internal:cluster/coordination/publish_state`
  - OpenSearch later fails publication with:
    - `FailedToCommitClusterStateException: publication failed`
    - `FailedToCommitClusterStateException: non-failed nodes do not form a quorum`
- current blocker:
  - membership is still not stably formed at the REST/probe level
  - the next missing implementation is no longer `start_join`
  - the next missing implementation is responding correctly to publication-stage traffic, starting with:
    - `internal:coordination/fault_detection/follower_check`
    - `internal:cluster/coordination/publish_state`

2026-05-03 follower-check response update

- latest actual artifact used for blocker confirmation:
  - `/tmp/java-rust-mixed-membership.PQZkp3/opensearch/stdout.log`
- change:
  - Steelsearch now returns `Empty` for `internal:coordination/fault_detection/follower_check`
  - it also keeps the transport channel open after the response instead of dropping it immediately
- confirmed:
  - despite the response path and hold-open change, OpenSearch still logs:
    - `FollowerChecker ... disconnected`
    - `FollowerChecker ... marking node as faulty`
  - publication still fails with:
    - `FailedToCommitClusterStateException: publication failed`
    - `FailedToCommitClusterStateException: non-failed nodes do not form a quorum`
- interpretation:
  - the remaining follower-check gap is not “no response path”
  - the remaining gap is that the followup transport channel still does not satisfy the persistent connection semantics OpenSearch expects for follower checks
  - until that is fixed, `publish_state` handling alone will not stabilize mixed membership

2026-05-03 publish-state inspection prep

- change:
  - transport capture now persists full `body_hex` for these actions:
    - `internal:coordination/fault_detection/follower_check`
    - `internal:cluster/coordination/publish_state`
    - `internal:cluster/coordination/start_join`
- reason:
  - the next missing implementation is a minimal `PublishWithJoinResponse`
  - to build that response correctly we need actual `publish_state` term/version from the captured request payload rather than guessing
- current next step:
  - add a decoder helper that reads captured `publish_state` `body_hex` and extracts actual publication term/version

2026-05-03 publish-state term/version decoder update

- latest actual artifacts:
  - `/tmp/java-rust-mixed-membership.LK3Vfy/steelsearch/data/transport-seed-capture.json`
  - `/tmp/publish-state-parse.xUk983.json`
- change:
  - added `tools/parse_java_publish_state_request.sh`
  - the helper reads captured `publish_state` `body_hex`, reconstructs `BytesTransportRequest`, decompresses the cluster-state payload, and extracts actual publication metadata
- confirmed:
  - for the captured `publish_state` request:
    - `full_state = true`
    - `term = 1`
    - `version = 1`
    - `cluster_name = mixed-java-rust-dev`
- implication:
  - the next missing implementation can now build a minimal `PublishWithJoinResponse` from actual payload values instead of guessing term/version

2026-05-03 publish-state runtime wiring update

- latest actual artifact used for validation:
  - `/tmp/java-rust-mixed-membership.ojnMZK/opensearch/stdout.log`
- change:
  - Steelsearch now calls the `publish_state` decoder helper at runtime and returns a minimal `PublishWithJoinResponse` built from the extracted `term/version`
- confirmed:
  - no new `term mismatch` or `version mismatch` error appeared in the OpenSearch log after wiring the runtime response path
  - however the cluster still fails in the same publication window with:
    - `FollowerChecker ... disconnected`
    - `FailedToCommitClusterStateException: publication failed`
    - `FailedToCommitClusterStateException: non-failed nodes do not form a quorum`
- interpretation:
  - the next missing piece is not just extracting `term/version`
  - the remaining blocker is still the end-to-end publication / follower liveness path after the initial `publish_state` response wiring

2026-05-03 publish-state optional-join runtime wiring update

- latest actual artifacts:
  - `/tmp/java-rust-mixed-membership.anhqwm/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.anhqwm/steelsearch/data/transport-seed-capture.json`
- change:
  - Steelsearch now includes a minimal optional `Join` inside `PublishWithJoinResponse`
  - join shape:
    - `sourceNode = rust-replica-1`
    - `targetNode = java-primary-1`
    - `term = publish_state.term`
    - `lastAcceptedTerm = 0`
    - `lastAcceptedVersion = 0`
- confirmed:
  - OpenSearch still repeatedly logs:
    - `FollowerChecker ... disconnected`
    - `FailedToCommitClusterStateException: publication failed`
    - `FailedToCommitClusterStateException: non-failed nodes do not form a quorum`
  - no new transport action appears after `internal:cluster/coordination/publish_state`
  - `internal:cluster/coordination/commit_state` is still not observed in the capture
- interpretation:
  - adding optional join to `PublishWithJoinResponse` was not enough to move publication to commit
  - the blocker remains in publication/follower liveness semantics, not in missing join payload shape alone

2026-05-03 publication lastAccepted term/version reuse update

- latest actual artifacts:
  - `/tmp/java-rust-mixed-membership.hHg28Z/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.hHg28Z/steelsearch/data/transport-seed-capture.json`
- change:
  - Steelsearch now remembers accepted `publish_state` `term/version`
  - subsequent outbound `internal:cluster/coordination/join` and optional join payloads reuse the remembered `lastAcceptedTerm/lastAcceptedVersion`
- confirmed:
  - OpenSearch join log now advances with matching carried state instead of staying at `0/0`
  - sampled progression:
    - `(term=1, lastAcceptedTerm=0, lastAcceptedVersion=0)`
    - `(term=2, lastAcceptedTerm=1, lastAcceptedVersion=1)`
    - `(term=78, lastAcceptedTerm=77, lastAcceptedVersion=77)`
  - despite that, OpenSearch still logs:
    - `FollowerChecker ... disconnected`
    - `FailedToCommitClusterStateException: publication failed`
    - `FailedToCommitClusterStateException: non-failed nodes do not form a quorum`
  - `internal:cluster/coordination/commit_state` is still not observed
- interpretation:
  - publication/join state reuse is no longer the missing piece
  - the remaining blocker is still follower liveness / publication completion semantics after accepted publish-state traffic
## 2026-05-03 Java serializer PublishWithJoinResponse fallback probe

- 구현:
  - `tools/build_java_publish_with_join_response.sh`
    - local OpenSearch jar serializer로 `PublishWithJoinResponse` payload hex 생성
  - `crates/os-node/src/main.rs`
    - `build_publish_with_join_response(...)`가 Java helper payload를 우선 시도
    - helper 실패 시 기존 manual serializer path로 fallback
- helper smoke:
  - `bash tools/build_java_publish_with_join_response.sh --term 1 --version 1 ...`
  - hex output 생성 확인
- actual probe artifact:
  - `/tmp/java-rust-mixed-membership.Bxb4h8/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.Bxb4h8/steelsearch/data/transport-seed-capture.json`
- actual 결과:
  - OpenSearch 로그:
    - `elected-as-cluster-manager ([2] nodes joined)` 반복
    - `FollowerChecker ... disconnected` 반복
    - `FailedToCommitClusterStateException: publication failed`
    - `FailedToCommitClusterStateException: non-failed nodes do not form a quorum`
  - transport capture observed actions:
    - `internal:tcp/handshake`
    - `internal:transport/handshake`
    - `internal:discovery/request_peers`
    - `internal:cluster/request_pre_vote`
    - `internal:cluster/coordination/start_join`
    - `internal:coordination/fault_detection/follower_check`
  - 이번 run에서는 `internal:cluster/coordination/publish_state`가 capture에 들어오지 않음
  - `internal:cluster/coordination/commit_state`도 여전히 미관측
- 해석:
  - `PublishWithJoinResponse` wire encoding을 Java serializer로 맞춰도 현재 blocker는 해소되지 않음
  - blocker는 여전히 `FollowerChecker`/publication completion semantics 쪽이며, 이번 run 기준으로는 publication 단계까지 안정적으로 재진입하지도 못함

## 2026-05-03 follower_check sent response frame capture

- 구현:
  - `crates/os-node/src/main.rs`
    - transport capture artifact에 `response_frame` 추가
    - 각 inbound request별로 Steelsearch가 실제로 쓴 response frame summary를 함께 저장
- actual probe artifact:
  - `/tmp/java-rust-mixed-membership.ssveyL/steelsearch/data/transport-seed-capture.json`
  - `/tmp/java-rust-mixed-membership.ssveyL/opensearch/stdout.log`
- actual 결과:
  - `internal:coordination/fault_detection/follower_check` entry마다 `response_frame` 존재
  - 대표 응답:
    - `request_id = 11`
    - `message_length = 19`
    - `status = 1`
    - `is_response = true`
    - `version_id = 137287827`
    - `body_prefix_hex = 000000000000000b01082ed893000000020000`
  - 즉 Steelsearch는 follower-check에 대해 actual response frame을 쓰고 있음
  - 그럼에도 Java/OpenSearch 쪽은 계속
    - `FollowerChecker ... disconnected`
    - `publication failed`
    - `non-failed nodes do not form a quorum`
    를 기록
- 해석:
  - 현재 blocker는 “follower_check 응답 미전송”이 아님
  - `Empty` response write 이후에도 OpenSearch가 이 channel을 성공한 follower-check transport로 인정하지 않는 것이 남은 문제

## 2026-05-03 follower_check connection end reason capture

- 구현:
  - `crates/os-node/src/main.rs`
    - transport capture artifact에 `connection_end` 추가
    - hold-open loop가 `remote_eof` / `idle_timeout` / `hold_window_elapsed`를 구분해 기록
- actual probe artifact:
  - `/tmp/java-rust-mixed-membership.cocnJj/steelsearch/data/transport-seed-capture.json`
  - `/tmp/java-rust-mixed-membership.cocnJj/opensearch/stdout.log`
- actual 결과:
  - `internal:coordination/fault_detection/follower_check` entry의 `connection_end = remote_eof`
  - 같은 entry에 `response_frame`도 존재
    - 예:
      - `request_id = 11`
      - `response_frame.message_length = 19`
      - `response_frame.status = 1`
  - 즉 순서는 다음과 같음:
    - Java/OpenSearch가 follower-check request 전송
    - Steelsearch가 actual `Empty` response frame write
    - 그 뒤 remote peer가 EOF로 connection 종료
- 해석:
  - 현재 blocker는 Steelsearch 쪽 “무응답”이나 “hold-open 미구현”이 아님
  - OpenSearch가 Steelsearch의 follower-check response/channel semantics를 받아들이지 않고 remote close로 끝내는 것이 직접 원인

## 2026-05-03 Java-Java follower_check reference capture harness

- 구현:
  - `tools/run-opensearch-dev.sh`
    - `OPENSEARCH_TRANSPORT_PUBLISH_HOST`
    - `OPENSEARCH_TRANSPORT_PUBLISH_PORT`
    지원 추가
  - `tools/capture_transport_proxy.py`
    - transport TCP proxy + frame capture 추가
    - request/response frame summary 기록
    - empty file bootstrap + `SIGTERM` 종료 시 persist 보강
- actual attempt:
  - work dir:
    - `/tmp/java-java-follower-check.DbQvhK`
  - proxy capture:
    - `/tmp/java-java-follower-check.DbQvhK/proxy/capture.json`
- actual 결과:
  - `capture_exists = true`
  - `frame_count = 0`
  - `follower_check_request_count = 0`
  - `matched_response_count = 0`
- 해석:
  - reference capture harness는 생겼고 empty-capture 자체는 artifact로 남음
  - 초기 empty-capture 문제는 proxy persist 쪽 결함이었고 수정됨

## 2026-05-03 Java-Java proxy handshake reference capture

- actual artifact:
  - `/tmp/java-java-follower-check.DbQvhK/proxy/capture.json`
  - `/tmp/java-java-follower-check.DbQvhK/primary.stdout`
- actual 결과:
  - proxy가 실제 Java-Java transport traffic을 capture
  - captured frames:
    - client -> server `internal:tcp/handshake`
    - server -> client tcp handshake response
    - client -> server `internal:transport/handshake`
    - server -> client transport identity response
  - 하지만 그 다음 Java primary log:
    - `completed handshake with ... but followup connection failed`
    - `ConnectTransportException ... general node connection failure`
    - `handshake failed because connection reset`
  - 따라서 proxy path에서는 follower-check까지 도달하지 못함
- 해석:
  - reference capture harness는 실제 transport handshake wire를 잡는 수준까지는 확보됨
  - 남은 reference-path blocker는 `follower_check`가 아니라, Java-Java proxy 경로의 followup connection reset
  - 즉 현재 proxy는 follower-check reference wire를 잡기 전에 connection profile 유지/forwarding semantics를 더 맞춰야 함

## 2026-05-03 Java-Java proxy per-connection worker rerun

- 구현:
  - `tools/capture_transport_proxy.py`
    - accept loop가 첫 연결에서 block되지 않도록 connection별 worker thread 처리로 변경
- actual rerun:
  - work dir:
    - `/tmp/java-java-follower-check.wgQDS2`
  - proxy capture:
    - `/tmp/java-java-follower-check.wgQDS2/proxy/capture.json`
- actual 결과:
  - `capture_exists = true`
  - `frame_count = 0`
  - `follower_check_request_count = 0`
  - `matched_response_count = 0`
- 해석:
  - proxy single-accept 병목 자체는 제거했지만, Java-Java reference path는 아직 안정적으로 재현되지 않음
  - 즉 reference-path blocker는 단순 accept serialization 하나로 설명되지 않음

## 2026-05-03 Java-Java proxy followup reset checker

- 구현:
  - `tools/check_java_proxy_followup_capture.py`
    - proxy `capture.json`과 Java primary log를 함께 읽어
      - action count
      - `followup connection failed`
      - `connection reset`
      를 기준으로 reference-path blocker를 분류
- actual validation:
  - 입력 artifact:
    - `/tmp/java-java-follower-check.DbQvhK/proxy/capture.json`
    - `/tmp/java-java-follower-check.DbQvhK/primary.stdout`
  - checker 결과:
    - `action_counts.internal:tcp/handshake = 1`
    - `action_counts.internal:transport/handshake = 1`
    - `followup_failed = true`
    - `connection_reset = true`
    - `result = followup_reset_blocked`
- 해석:
  - Java-Java reference path의 현재 blocker는 executable하게 `followup_reset_blocked`로 고정됨
  - 즉 follower-check reference wire 미확보의 직접 원인은 proxy path followup reset이며, Steelsearch mixed probe의 `FollowerChecker ... disconnected`와는 별도 단계 문제임

## 2026-05-03 actual mixed probe follower/publish blocker classification

- 구현:
  - `tools/check_java_rust_follower_publish_probe.py`
    - mixed probe `report.json`과 linked OpenSearch stdout를 읽어
      - `FollowerChecker ... disconnected` 존재 여부
      - `internal:cluster/coordination/publish_state` 관측 여부
      를 함께 분류
- actual artifact:
  - report:
    - `/tmp/java-rust-mixed-membership.k7FK5r/report.json`
  - OpenSearch stdout:
    - `/tmp/java-rust-mixed-membership.k7FK5r/opensearch/stdout.log`
- actual checker 결과:
  - `internal:coordination/fault_detection/follower_check = 32`
  - `internal:cluster/coordination/publish_state = 0`
  - `follower_disconnected = true`
  - `publish_state_observed = false`
  - `result = follower_disconnected_before_publish_state`
- 해석:
  - 이번 actual mixed probe는 blocker가 `publish_state` 단독으로 좁혀지지 않았음을 보여줌
  - 현재 직접 blocker는 `follower_check` 이후 Java/OpenSearch가 connection을 유지/수용하지 못하고 publication 이전에 끊는 경로임
  - 다음 구현 초점은 `publish_state` serializer 추가 조정보다 Java/OpenSearch의 `remote_eof` acceptance gap을 줄이는 쪽이 맞음

## 2026-05-03 follower_check request body decode

- 구현:
  - `tools/parse_java_follower_check_request.sh`
    - captured `follower_check` body hex에서
      - `action`
      - `parent_task_node`
      - `term`
      - `sender.name`
      - `sender.id`
      - `sender.ephemeral_id`
      를 추출
- actual artifact:
  - source report:
    - `/tmp/java-rust-mixed-membership.k7FK5r/report.json`
  - parsed output:
    - `/tmp/java-rust-mixed-membership.k7FK5r/follower-check-request-parsed.json`
- actual 결과:
  - `action = internal:coordination/fault_detection/follower_check`
  - `parent_task_node = ""`
  - `term = 1`
  - `sender.name = java-primary-1`
  - `sender.id = RB_hGbZLTb-Wfl9f1BGP8Q`
  - `sender.ephemeral_id = SEDUHgW4QualrWIDtXgDCQ`
- 해석:
  - actual `follower_check` request 자체는 정상적으로 Java primary identity를 싣고 들어옴
  - 남은 blocker는 request decode mismatch가 아니라, 이 요청에 대한 Steelsearch response/channel semantics를 Java/OpenSearch가 `remote_eof`로 끝내는 점임

## 2026-05-03 follower_check Empty response header minimization probe

- 구현:
  - `crates/os-node/src/main.rs`
    - `build_empty_transport_response(...)`를 generic 2-byte variable header 경로에서 분리
    - `Empty` response는 0-byte variable header로 직렬화
- actual artifact:
  - report:
    - `/tmp/java-rust-mixed-membership.0cL77G/report.json`
  - capture:
    - `/tmp/java-rust-mixed-membership.0cL77G/steelsearch/data/transport-seed-capture.json`
  - stdout:
    - `/tmp/java-rust-mixed-membership.0cL77G/opensearch/stdout.log`
- actual 결과:
  - `follower_check` response frame:
    - `body_len = 17`
    - `message_length = 17`
    - `body_prefix_hex = 000000000000000b01082ed89300000000`
  - 그럼에도:
    - `connection_end = remote_eof`
    - `FollowerChecker ... disconnected`
    - checker result:
      - `follower_disconnected_before_publish_state`
- 해석:
  - 기존 `message_length=19`의 trailing zero variable header가 direct blocker라는 가설은 기각됨
  - 남은 gap은 `Empty` response frame 길이 자체가 아니라, Java/OpenSearch가 follower-check channel을 성공으로 인정하는 더 높은 수준의 acceptance semantics임

## 2026-05-03 Java reference follower_check Empty response

- 구현:
  - `tools/dump_java_follower_check_empty_response.sh`
    - OpenSearch `NativeOutboundHandler.sendResponse(..., TransportResponse.Empty.INSTANCE, ...)`를 직접 호출해
      `internal:coordination/fault_detection/follower_check` reference frame hex를 dump
  - `tools/check_follower_check_empty_response_reference.py`
    - mixed probe capture의 `follower_check` response frame과 Java reference bytes를 비교
- Java reference 결과:
  - full frame:
    - `455300000013000000000000000b01082ed893000000020000`
  - 의미:
    - Java native outbound 기준 `follower_check Empty` response는 `message_length=19`와 2-byte zero variable header를 포함
- actual validation:
  - source artifact:
    - `/tmp/java-rust-mixed-membership.k7FK5r/report.json`
  - checker 결과:
    - `captured.body_prefix_hex = 000000000000000b01082ed893000000020000`
    - `java_reference_body_hex = 000000000000000b01082ed893000000020000`
    - `matches_reference = true`
- 해석:
  - Steelsearch가 원래 내보내던 `19-byte Empty` response bytes는 Java reference와 raw-byte 수준에서 일치함
  - 따라서 남은 blocker는 `follower_check Empty` response frame 자체의 wire mismatch가 아니라, 그 이후 Java/OpenSearch의 channel acceptance semantics임
  - 이에 따라 runtime은 17-byte experimental path에서 다시 Java-reference-consistent 19-byte path로 복구함

## 2026-05-03 follower_check transport contract extraction

- 구현:
  - `tools/extract_follower_check_transport_contract.py`
    - OpenSearch source에서 follower-check transport contract를 추출
- extraction 결과:
  - `action_name = internal:coordination/fault_detection/follower_check`
  - `timeout_symbol = followerCheckTimeout`
  - `request_type = PING`
  - `response_read_returns_empty_instance = true`
  - `handle_response_resets_failure_count = true`
  - `connect_transport_exception_maps_to_disconnected = true`
  - `empty_handler_instance_same_executor = true`
- 해석:
  - source 기준으로도 follower-check success 판정은 `Empty` response를 정상 수신해 failure count를 0으로 되돌리는 경로임
  - 반대로 현재 mixed probe의 `FollowerChecker ... disconnected`는 `ConnectTransportException` 계열로 분류되는 disconnect path임
  - 즉 남은 gap은 request type/timeout/response class가 아니라, `Type.PING` 채널을 Java/OpenSearch가 성공으로 인정하는 acceptance semantics임

## 2026-05-03 PING dedicated connection profile extraction

- 구현:
  - `tools/extract_ping_connection_profile_contract.py`
    - OpenSearch source에서 `Type.PING`가 어떤 connection profile bucket으로 라우팅되는지 추출
- extraction 결과:
  - `connections_per_node_ping_setting = CONNECTIONS_PER_NODE_PING`
  - `default_profile_has_dedicated_ping_bucket = true`
  - `ping_interval_setting = PING_SCHEDULE`
  - `tcp_transport_routes_type_via_handle_mapping = true`
- 해석:
  - source 기준 follower-check는 단순 generic transport가 아니라 dedicated `PING` bucket/channel로 라우팅됨
  - 따라서 남은 blocker는 `Empty` response wire가 아니라, Steelsearch transport listener가 Java/OpenSearch의 dedicated `PING` channel semantics를 아직 만족시키지 못하는 점으로 더 좁혀짐

## 2026-05-03 transport keepalive ping receive/echo implementation

- 구현:
  - `crates/os-node/src/main.rs`
    - `ES` + `int(-1)` keepalive ping frame을 별도 `Ping` event로 인식
    - server-side listener가 keepalive ping 수신 시 같은 6-byte frame을 즉시 echo
    - capture에는 `is_keepalive_ping = true`, `connection_end = keepalive_ping` 형태로 남기도록 확장
- actual probe 시도:
  - work dir:
    - `/tmp/java-rust-mixed-membership.je7qgD`
  - final artifact:
    - `/tmp/java-rust-mixed-membership.je7qgD/report.json`
  - checker:
    - `tools/check_java_rust_keepalive_probe.py /tmp/java-rust-mixed-membership.je7qgD/report.json`
  - actual 결과:
    - `keepalive_count = 0`
    - `follower_check_count = 31`
    - `publish_state_count = 0`
    - `follower_disconnected = true`
    - `result = keepalive_not_observed_and_follower_still_disconnected`
- 해석:
  - keepalive ping receive/echo 구현 자체는 들어감
  - 현재 mixed probe에서는 OpenSearch가 Steelsearch 쪽으로 dedicated keepalive ping을 실제로 보내는 증거가 없음
  - 동시에 follower-check는 반복 유입되지만 `publish_state`까지는 다시 진전되지 않음
  - 따라서 다음 남은 일은 keepalive echo 구현 자체가 아니라, Java/OpenSearch가 이 mixed path에서 `PING` dedicated channel을 어떤 조건에서 keepalive/live channel로 승격하는지 source/runtime 기준으로 더 좁히는 것임

## 2026-05-03 keepalive 0회 precondition 분리

- 구현:
  - `tools/check_java_rust_ping_schedule_preconditions.py`
    - actual mixed probe artifact
    - `tools/run-opensearch-dev.sh`
    - OpenSearch `TransportSettings.java`
    를 함께 읽어 keepalive `0`회의 source/runtime precondition을 분류
- actual 결과:
  - `source_default_disabled = true`
  - `launcher_overrides_ping_schedule = false`
  - `keepalive_count = 0`
  - `result = ping_schedule_disabled_by_default_and_not_overridden`
- 해석:
  - 현재 mixed probe에서 keepalive ping이 관측되지 않은 것은 acceptance gap만으로 설명되는 게 아니라, 그 전에 `transport.ping_schedule` 자체가 기본 `-1`로 비활성화되어 있기 때문임
  - `run-opensearch-dev.sh`도 `transport.ping_schedule`을 전혀 주입하지 않으므로, 현재 probe path에서는 keepalive `0`회가 source/runtime precondition과 일치함
  - 따라서 다음 직접 검증은 source default를 유지한 채 acceptance를 추론하는 것이 아니라, `transport.ping_schedule`을 명시적으로 켠 mixed probe를 다시 돌려 keepalive/publish_state 변화가 생기는지 보는 일임

## 2026-05-03 explicit `transport.ping_schedule=1s` mixed probe

- 구현:
  - `tools/run-opensearch-dev.sh`
    - `OPENSEARCH_PING_SCHEDULE` 지원 추가
  - `tools/probe_java_rust_mixed_membership.sh`
    - `JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_PING_SCHEDULE` pass-through 추가
  - `tools/check_java_rust_ping_schedule_enabled_probe.py`
    - explicit enable probe artifact를 분류하는 checker 추가
- actual probe:
  - env:
    - `JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_PING_SCHEDULE=1s`
  - artifact:
    - `/tmp/java-rust-mixed-membership.4eME6M/report.json`
- actual 결과:
  - `OpenSearch transport ping_schedule: 1s`가 stderr에 기록됨
  - `keepalive_count = 0`
  - `publish_state_count = 0`
  - `follower_check_count = 31`
  - `follower_disconnected = true`
  - `result = ping_schedule_enabled_but_no_keepalive_or_publish_state_progress`
- 해석:
  - keepalive `0`회는 더 이상 “default disabled”만으로 설명되지 않음
  - `ping_schedule=1s`를 명시적으로 켜도 mixed path에서는 keepalive가 실제로 관측되지 않고, blocker도 `FollowerChecker ... disconnected`에 그대로 머뭄
  - 따라서 다음 남은 일은 keepalive scheduler 자체가 꺼져 있었는지 여부가 아니라, `needsKeepAlivePing(lastAccessedTime <= lastPingRelativeMillis)` 조건상 현재 follower-check cadence가 idle window를 만들지 않는지 source/runtime 기준으로 더 좁히는 것임

## 2026-05-03 keepalive idle-window와 follower-check cadence 분리

- 구현:
  - `tools/extract_transport_keepalive_idle_contract.py`
    - `TransportKeepAlive.java`에서 idle-window keepalive 조건 추출
  - `tools/check_java_rust_follower_check_cadence.py`
    - actual mixed probe stdout에서 `FollowerChecker ... disconnected` 간격을 계산하고
      `ping_schedule`보다 짧은 cadence인지 분류
- source extraction 결과:
  - `register_node_connection_requires_non_negative_ping_interval = true`
  - `needs_keepalive_uses_last_accessed_delta = true`
  - `needs_keepalive_requires_idle_window = true`
  - 의미:
    - keepalive는 `lastAccessedTime <= lastPingRelativeMillis`일 때만 전송됨
- actual cadence 결과:
  - source artifact:
    - `/tmp/java-rust-mixed-membership.4eME6M/report.json`
  - checker 입력:
    - `ping_schedule_seconds = 1.0`
  - 출력:
    - `follower_disconnected_count = 76`
    - `gaps_below_schedule = 45`
    - `gaps_at_or_above_schedule = 30`
    - `min_gap_seconds = 0.496`
    - `max_gap_seconds = 2.002`
    - `keepalive_count = 0`
    - `publish_state_count = 0`
    - `result = logged_follower_check_gaps_cross_ping_schedule_without_keepalive`
- 해석:
  - current mixed probe에서는 `FollowerChecker ... disconnected` gap이 `1s`보다 짧은 경우와 긴 경우가 섞여 있음
  - 그런데도 keepalive는 여전히 `0`회이므로, stdout 로그 cadence만으로는 `needsKeepAlivePing(lastAccessedTime <= lastPingRelativeMillis)`의 실제 channel idle 상태를 충분히 설명하지 못함
  - 따라서 다음 직접 검증은 더 짧은 ping schedule을 다시 주입하는 것이 아니라, transport capture에 per-connection activity timestamp를 남겨 실제 `PING` channel idle window가 `1s`를 넘는지 보는 일임

## 2026-05-03 per-connection idle-window timestamp probe

- 구현:
  - `crates/os-node/src/main.rs`
    - transport capture에
      - `connection_started_at_ms`
      - `first_frame_received_at_ms`
      - `follow_up_frame_received_at_ms`
      - `post_follow_up_frame_received_at_ms`
      - `response_frame_sent_at_ms`
      - `connection_end_at_ms`
      를 추가
  - `tools/check_java_rust_ping_channel_idle_window.py`
    - `follower_check` connection별 `response_frame_sent_at_ms -> connection_end_at_ms` 구간이
      `1s` idle window를 넘는지 검사
- actual probe:
  - artifact:
    - `/tmp/java-rust-mixed-membership.idlewindow/report.json`
  - env:
    - `JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_PING_SCHEDULE=1s`
- actual 결과:
  - `follower_check_window_count = 29`
  - `min_window_ms = 208`
  - `max_window_ms = 644`
  - `keepalive_count = 0`
  - `result = follower_check_channel_closes_before_ping_idle_window`
- representative samples:
  - `response_frame_sent_at_ms = 1777812252684`
  - `connection_end_at_ms = 1777812252892`
  - `connection_end = remote_eof`
- 해석:
  - current mixed probe에서는 `follower_check` dedicated `PING` channel이 응답 후 `208ms~644ms` 안에 `remote_eof`로 종료됨
  - 따라서 `transport.ping_schedule=1s`를 켜도 actual channel이 `1s` idle window에 도달하지 못해 keepalive가 발생하지 않는 설명이 성립함
  - 다음 남은 일은 ping schedule 값이 아니라, 이 `PING` channel이 왜 Java/OpenSearch 쪽에서 `remote_eof`로 조기 종료되는지 acceptance/persistence semantics를 더 분리하는 것임

## 2026-05-03 follower_check reusable PING connection contract vs actual fresh socket

- 구현:
  - `tools/extract_follower_check_connection_reuse_contract.py`
    - `FollowersChecker -> TransportService -> TcpTransport.NodeChannels` 경로에서
      follower-check가 reusable `Type.PING` node connection을 쓰는지 추출
  - `tools/check_java_rust_follower_check_channel_reuse.py`
    - actual mixed probe artifact에서 follower-check가 socket을 재사용하는지 검사
- source extraction 결과:
  - `followers_checker_uses_transport_service_send_request = true`
  - `followers_checker_requests_type_ping = true`
  - `transport_service_send_request_uses_get_connection = true`
  - `transport_service_get_connection_uses_connection_manager = true`
  - `tcp_transport_node_channels_route_by_request_type = true`
  - `tcp_transport_has_dedicated_type_channel_lookup = true`
- actual artifact 결과:
  - source artifact:
    - `/tmp/java-rust-mixed-membership.idlewindow/report.json`
  - checker 출력:
    - `follower_check_count = 29`
    - `unique_peer_addr_count = 29`
    - `result = follower_check_arrives_on_fresh_socket_every_time`
- 해석:
  - source 기준 follower-check는 `connectionManager.getConnection(node)`가 보유한 reusable node connection의 `Type.PING` channel을 타야 함
  - 그런데 actual mixed artifact에서는 follower-check가 `29/29` 전부 새 peer socket으로 유입됨
  - 따라서 남은 gap은 단순 `remote_eof` 현상이 아니라, OpenSearch가 Steelsearch를 reusable connected node channel로 유지하지 못하고 매번 fresh socket으로 다시 dial하는 점임

## 2026-05-03 coordinator path 전체의 fresh-socket arrival

- 구현:
  - `tools/check_java_rust_transport_connection_reuse.py`
    - actual mixed probe artifact에서 coordinator path 주요 action들의 socket reuse 여부를 검사
- actual 결과:
  - source artifact:
    - `/tmp/java-rust-mixed-membership.idlewindow/report.json`
  - checker 출력:
    - `internal:transport/handshake`: `28/28` unique
    - `internal:discovery/request_peers`: `44/44` unique
    - `internal:cluster/request_pre_vote`: `29/29` unique
    - `internal:coordination/fault_detection/follower_check`: `29/29` unique
    - `result = all_major_coordinator_actions_arrive_on_fresh_sockets`
- 해석:
  - fresh-socket 현상은 `follower_check` 하나의 예외가 아니라, handshake 이후 coordinator path 전체에 걸쳐 나타남
  - 따라서 다음 남은 분해 단위는 `follower_check` 전용 `PING` channel이 아니라, 그보다 앞선 `completed handshake -> connected node channel retention` 단계임

## 2026-05-03 followup connection retention failure contract

- 구현:
  - `tools/extract_followup_connection_retention_contract.py`
    - `HandshakingTransportAddressConnector`와 `ClusterConnectionManager`에서
      `probe handshake -> connectToNode -> retention failure` contract 추출
  - `tools/check_java_rust_followup_retention_failure.py`
    - actual mixed probe stdout가 이 followup failure 단계에 머무는지 분류
- source extraction 결과:
  - `probe_connection_uses_single_reg_channel_profile = true`
  - `handshake_success_closes_probe_connection_before_full_connect = true`
  - `full_connection_happens_via_transport_service_connect_to_node = true`
  - `warns_completed_handshake_but_followup_connection_failed = true`
  - `cluster_connection_manager_rejects_closed_channel_while_connecting = true`
- actual artifact 결과:
  - source artifact:
    - `/tmp/java-rust-mixed-membership.idlewindow/report.json`
  - checker 출력:
    - `completed_handshake_followup_failed = true`
    - `general_node_connection_failure = true`
    - `connection_reset = true`
    - `result = handshake_succeeded_but_followup_connection_failed_before_retention`
- 해석:
  - current mixed probe는 reusable node connection retention 이전 단계에서 멈춤
  - 즉 probe handshake는 성공하지만, 그 다음 `connectToNode()` full connection이 닫힌 채로 돌아와 reusable channel retention으로 승격되지 못함
  - 다음 남은 일은 `a channel closed while connecting`가 Steelsearch transport retention semantics 중 어디서 만들어지는지 더 분리하는 것임

## 2026-05-03 identity response 후 followup transport channel 종료 이유

- 구현:
  - `crates/os-node/src/main.rs`
    - `internal:transport/handshake`
    - `request_peers`
    - `request_pre_vote`
    - `start_join`
    경로도 `connection_end`/timestamp를 실제로 남기도록 보강
  - `tools/check_java_rust_followup_transport_channel_end.py`
    - followup transport channel이 identity response 뒤 어떻게 끝나는지 검사
- actual probe:
  - artifact:
    - `/tmp/java-rust-mixed-membership.followup-end/report.json`
- actual 결과:
  - `transport_handshake_count = 28`
  - `remote_eof_after_identity_count = 28`
  - `idle_timeout_after_identity_count = 0`
  - `post_follow_up_frame_count = 0`
  - `result = identity_response_followup_channel_always_remote_eof`
- representative sample:
  - `response_frame_sent_at_ms = 1777812799745`
  - `connection_end_at_ms = 1777812800154`
  - `connection_end = remote_eof`
- 해석:
  - current mixed probe에서는 followup full connection이 `internal:transport/handshake` identity response까지는 받음
  - 그러나 그 이후 reusable node channel로 유지되지 못하고, every case가 `post_follow_up_frame` 없이 `remote_eof`로 종료됨
  - 따라서 남은 gap은 generic `a channel closed while connecting`에서 더 좁혀져, `identity response 후 channel retention` 자체가 성립하지 않는 점임

## 2026-05-03 followup transport channel early-close window

- 구현:
  - `tools/check_java_rust_followup_transport_window.py`
    - `internal:transport/handshake` response 후 `connection_end_at_ms - response_frame_sent_at_ms` window를 측정
- actual 결과:
  - source artifact:
    - `/tmp/java-rust-mixed-membership.followup-end/report.json`
  - checker 출력:
    - `window_count = 28`
    - `min_window_ms = 407`
    - `max_window_ms = 807`
    - `threshold_ms = 1000`
    - `result = followup_transport_channel_closes_quickly_after_identity_response`
- 해석:
  - followup full connection은 long-idle 이후에 정리되는 게 아니라, identity response 후 `407ms~807ms` 안에 peer가 조기 종료함
  - 따라서 다음 남은 일은 generic retention 실패가 아니라, 이 `sub-second remote_eof`를 Java/OpenSearch peer가 왜 발생시키는지 더 분리하는 것임

## 2026-05-03 first channel close -> full connection failure fan-out contract

- 구현:
  - `tools/extract_followup_close_fanout_contract.py`
    - `TcpTransport.NodeChannels`와 `ClusterConnectionManager`에서
      single channel close가 full node connection failure로 fan-out되는 contract 추출
- source extraction 결과:
  - `node_channels_register_per_channel_close_listener = true`
  - `node_channels_close_closes_all_channels = true`
  - `cluster_connection_manager_fails_if_connection_already_closed = true`
- 해석:
  - source 기준으로 full `connectToNode()`는 multi-channel `NodeChannels`를 구성한 뒤,
    채널 하나라도 닫히면 `nodeChannels::close`가 나머지 채널도 함께 닫음
  - 그리고 `ClusterConnectionManager`는 그 시점에 `a channel closed while connecting`으로 full connection을 실패 처리함
  - 따라서 현재 남은 root gap은 “왜 full connection이 실패하느냐”가 아니라,
    “왜 Java/OpenSearch peer가 first followup channel을 identity response 직후 닫느냐”로 더 좁혀짐

## 2026-05-03 tcp-handshake-only channel hold-open 효과

- 구현:
  - `crates/os-node/src/main.rs`
    - `tcp/handshake` response 뒤 immediate follow-up이 없어도 channel을 바로 drop하지 않고 hold-open 하도록 수정
- actual probe:
  - artifact:
    - `/tmp/java-rust-mixed-membership.tcp-hold/report.json`
- actual 결과:
  - `check_java_rust_followup_retention_failure.py`:
    - `completed_handshake_followup_failed = false`
    - `general_node_connection_failure = false`
    - `connection_reset = false`
    - `result = followup_retention_failure_not_observed`
  - `check_java_rust_follower_publish_probe.py`:
    - `publish_state_observed = true`
    - `follower_disconnected = true`
    - `result = follower_disconnected_with_publish_state`
  - action counts:
    - `internal:cluster/coordination/publish_state = 2`
- 해석:
  - `tcp/handshake-only` channel을 즉시 drop하던 경로는 실제 blocker 중 하나였음
  - 이 수정으로 `completed handshake ... but followup connection failed` 단계는 사라지고, publication 단계까지 다시 진전됨
  - 따라서 현재 blocker는 더 이상 `before_publish_state`가 아니라 `follower_disconnected_with_publish_state` 상태임

## 2026-05-03 publish_state reached / commit_state blocked classification

- 구현:
  - `tools/check_java_rust_publish_commit_blocker.py`
    - actual mixed probe artifact에서
      - `publish_state`
      - `commit_state`
      - `FollowerChecker`
      - `publication failed`
    를 함께 분류
- actual 결과:
  - source artifact:
    - `/tmp/java-rust-mixed-membership.tcp-hold/report.json`
  - checker 출력:
    - `publish_state_count = 2`
    - `commit_state_count = 0`
    - `follower_disconnected = true`
    - `publication_failed = true`
    - `result = publish_state_reached_commit_state_blocked`
- 해석:
  - current mixed probe는 publication 단계까지는 도달하지만, `commit_state`는 아직 한 번도 관측되지 않음
  - 따라서 다음 남은 일은 generic publish blocker가 아니라, `commit_state` 미관측 상태를 기준으로 publication/commit acceptance gap을 더 분리하는 것임

## 2026-05-03 commit_state quorum suppression contract

- 구현:
  - `tools/extract_commit_state_quorum_contract.py`
    - `CoordinationState.handlePublishResponse()`와 `Publication`에서
      `commit_state`가 quorum 뒤에만 나가는 contract 추출
  - `tools/check_java_rust_commit_state_quorum_blocker.py`
    - actual mixed probe에서 `commit_state` 미관측이 quorum failure 때문인지 분류
- source extraction 결과:
  - `handle_publish_response_returns_optional_apply_commit = true`
  - `apply_commit_emitted_only_on_publish_response_success = true`
  - `publication_reports_non_failed_nodes_do_not_form_quorum = true`
  - `publication_sends_apply_commit_only_after_publish_phase = true`
- actual 결과:
  - source artifact:
    - `/tmp/java-rust-mixed-membership.tcp-hold/report.json`
  - checker 출력:
    - `publish_state_count = 2`
    - `commit_state_count = 0`
    - `quorum_failure = true`
    - `publication_failed = true`
    - `result = commit_state_suppressed_by_quorum_failure`
- 해석:
  - current mixed probe에서 `commit_state`가 안 오는 직접 이유는 publish phase 뒤 quorum이 성립하지 않기 때문임
  - 따라서 다음 남은 일은 `commit_state` serializer가 아니라, publication quorum이 왜 성립하지 않는지 더 분리하는 것임
- 2026-05-03 `publish_state` quorum blocker refinement:
  - source contract:
    - `PublicationTarget.PublishResponseHandler.onResponse(...)`는 `WAITING_FOR_QUORUM`으로 전이한 뒤 `handlePublishResponse(...)`를 호출
    - `PublishResponseHandler.onFailure(...)`는 `TransportException`을 받아 `setFailed(...)` 후 `onPossibleCommitFailure()`를 호출
    - 즉 publish phase transport failure는 곧바로 quorum/commit failure로 이어짐
  - actual artifact:
    - `/tmp/java-rust-mixed-membership.tcp-hold/report.json`
    - `publish_state_count = 2`
    - `response_written_count = 2`
    - `same_tick_remote_eof_count = 2`
    - `commit_state_count = 0`
    - `result = publish_state_response_written_but_same_tick_remote_eof_before_commit_state`
  - 의미:
    - current blocker는 단순히 `commit_state`가 안 온다는 수준이 아니라
    - `publish_state` response를 실제로 쓴 직후 connection이 같은 tick에 `remote_eof`로 접히면서 publish quorum이 transport failure로 무너지는 패턴임

- 2026-05-03 `publish_state` channel retention refinement:
  - source contract:
    - `PublicationTransportHandler.stateRequestOptions`는 `TransportRequestOptions.Type.STATE`
    - source 주석도 `response를 eventually receive`하려고 timeout을 두지 않는다고 명시
    - 실제 `PUBLISH_STATE_ACTION_NAME` 전송도 `stateRequestOptions`를 사용
  - actual artifact:
    - `/tmp/java-rust-mixed-membership.tcp-hold/report.json`
    - `publish_state_count = 2`
    - `same_tick_remote_eof_count = 2`
    - `result = publish_state_state_channel_same_tick_remote_eof_every_time`
  - 의미:
    - source expectation은 `STATE` / no-timeout publication channel인데
    - actual mixed probe에서는 `publish_state` 응답 직후 channel이 같은 tick에 닫힘
    - 따라서 다음 남은 gap은 generic quorum failure가 아니라 `STATE` publication channel close가 Java/OpenSearch target failure로 어떻게 해석되는지임

- 2026-05-03 `publish_state` target failure contract:
  - source contract:
    - `PublishResponseHandler.onFailure(...)`는 `setFailed(...)` 후 `onPossibleCommitFailure()`를 호출
    - `onFaultyNode(...)`도 `setFailed(...)` 후 `onPossibleCommitFailure()`를 호출
    - 즉 publication target의 transport failure는 곧바로 commit/quorum failure 판단으로 연결됨
  - actual artifact:
    - `/tmp/java-rust-mixed-membership.tcp-hold/report.json`
    - `publish_state_count = 2`
    - `same_tick_remote_eof_count = 2`
    - `publication_failed = true`
    - `quorum_failure = true`
    - `result = publish_state_channel_close_interpreted_as_target_failure`
  - 의미:
    - current mixed probe는 `publish_state` channel close가 실제로 publication target failure와 quorum failure로 이어지는 상태까지는 고정됨
    - 다음 남은 질문은 왜 Java/OpenSearch가 아니라 Steelsearch side에서 publication `STATE` channel을 즉시 닫히게 만드는가임

- 2026-05-03 Steelsearch `publish_state` hold-open contract vs actual EOF:
  - runtime contract:
    - `main.rs`의 `internal:cluster/coordination/publish_state` branch는
      - response write
      - flush
      - `response_frame_sent_at_ms`
      - `hold_transport_channel_open(..., Duration::from_secs(20), ...)`
      를 모두 수행
  - actual artifact:
    - `/tmp/java-rust-mixed-membership.tcp-hold/report.json`
    - `publish_state_count = 2`
    - `remote_eof_count = 2`
    - `same_tick_count = 2`
    - `max_window_ms = 0`
    - `result = publish_state_peer_eof_arrives_before_local_hold_open_window_matters`
  - 의미:
    - local runtime은 publication `STATE` channel을 바로 닫지 않음
    - actual close는 `20s` hold-open이 의미를 가지기 전에 peer 쪽 EOF가 먼저 도착하는 패턴임
    - 따라서 다음 남은 gap은 `Steelsearch closes immediately`가 아니라 `Java/OpenSearch peer가 왜 publication STATE channel에 즉시 EOF를 보내는가`임

- 2026-05-03 `publish_state` response decode check:
  - runtime change:
    - `publish_state` response `body_hex`를 actual artifact에 남기도록 capture 확장
  - actual artifact:
    - `/tmp/java-rust-mixed-membership.YVGEkE/report.json`
    - `publish_state_count = 2`
    - `decoded_count = 2`
    - `all_join_present = true`
    - `decoded_terms = [1, 2]`
    - `decoded_versions = [1, 2]`
    - `result = publish_state_response_decodes_as_valid_publish_with_join_response`
  - 의미:
    - current peer EOF는 `PublishWithJoinResponse` serializer/decode mismatch 때문이 아님
    - Java/OpenSearch peer는 response body 자체는 정상적으로 읽을 수 있는데도 `STATE` channel을 즉시 닫음
    - 따라서 다음 남은 gap은 `valid response 이후 channel retention/acceptance semantics` 쪽임

- 2026-05-03 reusable `STATE` channel contract vs actual failure:
  - source contract:
    - `publish_state`는 `stateRequestOptions(Type.STATE)`로 전송됨
    - `TransportService.sendRequest(...)`는 `getConnection(node)`를 사용
    - `getConnection(node)`는 `connectionManager.getConnection(node)`를 사용
    - default connection profile에는 dedicated `STATE` bucket이 존재
  - actual artifact:
    - `/tmp/java-rust-mixed-membership.YVGEkE/report.json`
    - `publish_state_count = 2`
    - `valid_decode_artifact_count = 2`
    - `same_tick_remote_eof_count = 2`
    - `result = valid_publish_state_response_still_fails_reusable_state_channel_retention`
  - 의미:
    - source expectation은 reusable `STATE` node channel인데
    - actual mixed probe에서는 valid `PublishWithJoinResponse` 이후에도 channel retention이 성립하지 않음
    - 따라서 다음 남은 gap은 `response validity`가 아니라 `STATE channel acceptance/retention semantics`임

- 2026-05-03 `STATE` channel close fan-out contract:
  - source contract:
    - `NodeChannels`는 `type -> channel handle` 매핑을 유지
    - 각 channel close listener가 `nodeChannels::close`를 호출
    - `NodeChannels.close()`는 해당 node connection의 모든 channels를 닫음
  - actual artifact:
    - `/tmp/java-rust-mixed-membership.YVGEkE/report.json`
    - `publish_state_count = 2`
    - `same_tick_remote_eof_count = 2`
    - `commit_state_count = 0`
    - `result = state_channel_close_fanout_blocks_commit_state_progress`
  - 의미:
    - current mixed probe에서는 publication `STATE` channel close가 per-channel 문제가 아니라 node-level channel set failure로 fan-out될 조건을 만족
    - 그 결과 `commit_state`까지 진전하지 못하는 상태로 해석 가능

- 남은 불명확성:
  - 현재까지의 근거는 mixed Java-Rust actual probe 기준임
  - 아직 `Java-Java reference path`에서 `publish_state` `STATE` channel이 같은 방식으로 닫히는지, 그리고 `commit_state` 정체가 동일한지에 대한 capture는 없음
  - 다음 비교 기준은 `Java-Java reference에서도 publish_state close / commit_state blocked`가 재현되는지 여부임

- 2026-05-03 Java-Java publish_state reference run:
  - runner:
    - `tools/run_java_java_publish_state_reference.sh`
  - actual artifact:
    - work dir: `/tmp/java-java-publish-state.93FzXm`
    - proxy capture: `/tmp/java-java-publish-state.93FzXm/proxy/capture.json`
    - primary stdout: `/tmp/java-java-publish-state.93FzXm/primary/stdout.log`
  - checker result:
    - `publish_state_count = 0`
    - `commit_state_count = 0`
    - `handshake_count = 20`
    - `followup_failed = true`
    - `publication_failed = false`
    - `result = stalled_at_followup_connection`
  - 의미:
    - current Java-Java reference path는 `publish_state` 단계 비교에 아직 도달하지 못함
    - baseline blocker도 mixed 경로와 비슷하게 `followup connection` 단계에서 먼저 막힘

- 2026-05-03 Java-Java reference rerun after proxy half-close fix:
  - proxy change:
    - `capture_transport_proxy.py`가 EOF 시 peer socket을 바로 close하지 않고 `shutdown(SHUT_WR)`로 half-close를 전달
  - actual artifact:
    - work dir: `/tmp/java-java-publish-state.Mfda2y`
    - proxy capture: `/tmp/java-java-publish-state.Mfda2y/proxy/capture.json`
    - primary stdout: `/tmp/java-java-publish-state.Mfda2y/primary/stdout.log`
  - checker result:
    - `publish_state_count = 0`
    - `commit_state_count = 0`
    - `handshake_count = 95`
    - `followup_failed = true`
    - `result = stalled_at_followup_connection`
  - 의미:
    - proxy close semantics가 direct blocker였다면 이 rerun에서 최소 `publish_state` 단계까지는 전진했어야 함
    - 하지만 half-close 적용 후에도 reference baseline은 여전히 `completed handshake ... but followup connection failed`에서 멈춤
    - 따라서 next gap은 proxy reset이 아니라 Java/OpenSearch 자체의 followup connection acceptance 조건임

- 2026-05-03 direct Java-Java baseline:
  - runner:
    - `tools/run_java_java_direct_baseline.sh`
  - actual artifact:
    - work dir: `/tmp/java-java-direct.LdvDMM`
  - result:
    - `observed_node_count = 2`
  - 의미:
    - proxy 없는 direct Java-Java baseline은 실제로 2-node cluster를 형성함
    - 따라서 current reference blocker는 Java/OpenSearch same-version cluster 자체가 아니라 `proxy publish/followup connection` 경로에 국한됨

- 2026-05-03 direct vs proxy comparison:
  - comparison checker:
    - `tools/check_java_java_proxy_specific_followup_blocker.py`
  - inputs:
    - direct baseline: `/tmp/java-java-direct.LdvDMM`
    - proxy reference check: `/tmp/java-java-publish-state.Mfda2y`
  - result:
    - `direct_observed_node_count = 2`
    - `proxy_publish_state_count = 0`
    - `proxy_followup_failed = true`
    - `result = direct_java_java_cluster_forms_but_proxy_reference_stalls_at_followup_connection`
  - 의미:
    - Java-Java 자체는 붙지만, proxy publish path를 끼우면 `publish_state` 이전 `followup connection`에서 정지
    - 따라서 reference capture의 현재 미완료는 publication logic이 아니라 proxy-specific followup acceptance blocker임

- 2026-05-03 direct Java-Java transport trace reference:
  - runner:
    - `tools/run_java_java_transport_trace_reference.sh`
  - actual artifact:
    - run json: `/tmp/java-java-trace.latest.json`
    - work dir: `/tmp/java-java-trace.SiZF5H`
  - checker result:
    - `publish_state_count = 24`
    - `commit_state_count = 24`
    - `result = publish_state_observed_in_transport_trace`
  - tracer evidence:
    - follower:
      - `internal:cluster/coordination/publish_state` received request / sent response
      - `internal:cluster/coordination/commit_state` received request / sent response
    - primary:
      - `internal:cluster/coordination/publish_state` sent / received response
      - `internal:cluster/coordination/commit_state` sent / received response
  - 의미:
    - Java-Java reference baseline에서는 `publish_state`와 `commit_state`가 모두 실제로 관측됨
    - 따라서 mixed path의 `commit_state` 정체는 Java/OpenSearch reference behavior가 아니라 mixed transport acceptance 문제임
    - 동시에 proxy reference path가 `publish_state` 이전 `followup connection`에서 멈추는 것도 direct baseline과 대비해 확인됨

- 2026-05-03 tracer vs proxy comparison:
  - comparison checker:
    - `tools/check_java_java_tracer_vs_proxy_followup_gap.py`
  - inputs:
    - tracer check: `/tmp/java-java-trace.latest.check.json`
    - proxy check: `/tmp/java-java-publish-state.Mfda2y/proxy-check.json`
  - result:
    - `tracer_publish_state_count = 24`
    - `tracer_commit_state_count = 24`
    - `proxy_publish_state_count = 0`
    - `proxy_followup_failed = true`
    - `result = proxy_path_stalls_before_publish_state_while_direct_tracer_reaches_commit_state`
  - 의미:
    - Java-Java reference baseline은 publication/commit까지 정상 진전
    - proxy reference path만 `publish_state` 이전 `followup connection` 단계에서 멈춤
    - 따라서 다음 남은 gap은 publication logic 비교가 아니라 proxy path의 followup acceptance contract임

- 2026-05-03 Java-Java proxy followup acceptance checker:
  - checker:
    - `tools/check_java_java_proxy_followup_acceptance.py`
  - input:
    - `/tmp/java-java-publish-state.Mfda2y/proxy/capture.json`
    - `/tmp/java-java-publish-state.Mfda2y/primary/stdout.log`
  - result:
    - `tcp_handshake_count = 55`
    - `transport_handshake_count = 40`
    - `publish_state_count = 0`
    - `followup_failed = true`
    - `connection_reset = true`
    - `result = proxy_reference_fails_followup_acceptance_before_publish_state`
  - 의미:
    - proxy reference path는 handshake wire는 충분히 보이지만
    - `publish_state` 이전 `followup connection` acceptance 자체가 성립하지 않음

- 2026-05-03 old mixed vs current mixed vs Java-Java proxy:
  - comparison checker:
    - `tools/check_mixed_vs_proxy_followup_gap.py`
  - result:
    - `mixed_followup_remote_eof_after_identity_count = 28`
    - `mixed_publish_state_count = 2`
    - `mixed_commit_state_count = 0`
    - `proxy_followup_failed = true`
    - `proxy_publish_state_count = 0`
    - `result = proxy_reference_matches_old_mixed_followup_failure_but_differs_from_current_mixed_publish_state_progress`
  - 의미:
    - Java-Java proxy reference path는 current mixed와 직접 같은 단계에 있지 않음
    - 오히려 `tcp/handshake-only hold-open` 이전 old mixed followup-fail 패턴과 더 가깝게 정렬됨
    - 따라서 다음 남은 gap은 `왜 proxy path가 current mixed처럼 publish_state까지 진전하지 못하는가`라는 runtime 차이 축임

- 2026-05-03 current mixed hold-open vs Java-Java proxy:
  - source/runtime contract:
    - `main.rs`의 `tcp/handshake` branch는 optional follow-up을 읽고
    - follow-up이 없어도 `hold_transport_channel_open(..., Duration::from_secs(15), ...)`를 수행
  - extractor result:
    - `tcp_handshake_branch_present = true`
    - `tcp_handshake_reads_optional_follow_up = true`
    - `tcp_handshake_followup_identity_hold_open = true`
    - `tcp_handshake_no_followup_hold_open_15s = true`
  - comparison result:
    - `mixed_followup_failed = false`
    - `mixed_connection_reset = false`
    - `proxy_followup_failed = true`
    - `proxy_publish_state_count = 0`
    - `result = mixed_tcp_handshake_hold_open_eliminates_followup_failure_but_proxy_path_still_stalls_before_publish_state`
  - 의미:
    - current mixed path는 `tcp/handshake-only hold-open` 이후 followup failure를 넘어서 `publish_state`까지 진전
    - Java-Java proxy reference는 같은 단계로 못 올라오고 여전히 pre-publish followup acceptance에서 멈춤

- 2026-05-03 current mixed hold-open contract vs Java-Java proxy pre-publish stall:
  - checker:
    - `tools/check_probe_close_contract_vs_mixed_proxy.py`
  - inputs:
    - `/tmp/current-mixed-hold-open-contract.json`
    - `/tmp/current-mixed-followup.json`
    - `/tmp/java-java-proxy-followup.json`
  - result:
    - `hold_open_contract_present = true`
    - `mixed_followup_failed = false`
    - `mixed_connection_reset = false`
    - `proxy_followup_failed = true`
    - `proxy_publish_state_count = 0`
    - `result = current_mixed_hold_open_contract_present_but_java_java_proxy_still_stalls_pre_publish`
  - 의미:
    - current mixed는 `tcp/handshake-only hold-open` 계약이 실제로 followup failure 제거까지 이어짐
    - Java-Java proxy path는 같은 acceptance 효과를 얻지 못하고 여전히 `publish_state` 이전에서 정체
    - 다음 남은 질문은 proxy path에 current mixed와 동등한 runtime acceptance 조건이 왜 성립하지 않는가임

- 2026-05-03 Java-Java proxy runtime contract vs current mixed hold-open:
  - extractor/checker:
    - `tools/extract_proxy_followup_runtime_contract.py`
    - `tools/check_mixed_hold_open_vs_proxy_runtime_contract.py`
  - result:
    - `mixed_hold_open_contract_present = true`
    - `proxy_forwards_bytes_transparently = true`
    - `proxy_propagates_eof_via_half_close = true`
    - `proxy_opens_new_upstream_per_accept = true`
    - `proxy_has_application_level_followup_hold_open = false`
    - `result = proxy_runtime_lacks_current_mixed_application_level_hold_open_acceptance_conditions`
  - 의미:
    - current mixed의 진전은 application-level hold-open override 효과임
    - Java-Java proxy는 pure pass-through라 같은 acceptance 조건을 만들지 못함
    - 따라서 다음 reference baseline 일감은 proxy를 통해 publication을 보겠다는 가정 자체보다, publication까지 갈 수 있는 덜 교란적인 capture 경로를 확보하는 쪽이 맞음

- 2026-05-03 less-intrusive Java-Java publication reference path:
  - checker:
    - `tools/check_java_java_less_intrusive_reference_capture.py`
  - inputs:
    - `/tmp/java-java-trace.latest.check.json`
    - `/tmp/java-java-publish-state.Mfda2y/proxy-check.json`
  - result:
    - `tracer_publish_state_count = 24`
    - `tracer_commit_state_count = 24`
    - `proxy_publish_state_count = 0`
    - `proxy_followup_failed = true`
    - `result = direct_tracer_is_less_intrusive_publication_observable_reference_path`
  - 의미:
    - 현재 usable Java-Java reference baseline은 proxy capture가 아니라 direct transport tracer 경로임
    - mixed path와 publication/retention 차이를 비교할 다음 기준 artifact는 direct tracer baseline에서 뽑는 게 맞음

- 2026-05-03 normalized publication baseline:
  - checker:
    - `tools/check_publication_reference_normalization.py`
  - inputs:
    - `/tmp/java-java-trace.latest.check.json`
    - `/tmp/java-rust-mixed-publish-commit.json`
    - `/tmp/java-rust-mixed-state-close.json`
  - result:
    - reference:
      - `publication_progress_class = publish_and_commit_observed`
      - `state_channel_retention_class = retained_through_commit`
    - mixed:
      - `publication_progress_class = publish_reached_commit_blocked`
      - `state_channel_retention_class = same_tick_remote_eof_before_commit`
    - `result = canonical_reference_and_mixed_publication_baselines_normalized`
  - 의미:
    - direct tracer baseline은 publication success/reference 축으로 충분함
    - current mixed는 같은 축에서 `STATE` channel retention 실패 때문에 `commit_state` 전진이 막힌 상태로 정규화됨

- 2026-05-03 direct reference vs mixed STATE channel acceptance gap:
  - checker:
    - `tools/check_state_channel_acceptance_gap.py`
  - inputs:
    - `/tmp/state-channel-contract.json`
    - `/tmp/normalized-publication-baseline.json`
  - result:
    - `reusable_state_channel_contract = true`
    - `reference_state_channel_retention_class = retained_through_commit`
    - `mixed_state_channel_retention_class = same_tick_remote_eof_before_commit`
    - `reference_publication_progress_class = publish_and_commit_observed`
    - `mixed_publication_progress_class = publish_reached_commit_blocked`
    - `result = reusable_state_channel_contract_holds_in_reference_but_fails_in_mixed_acceptance`
  - 의미:
    - 남은 gap은 `publish_state` response validity나 source contract 해석 문제가 아님
    - reusable `STATE` channel contract는 reference에서 실제로 성립하고, mixed path에서만 acceptance/retention이 깨짐

- 2026-05-03 mixed publish_state socket trigger:
  - checker:
    - `tools/check_mixed_publish_state_socket_trigger.py`
  - input:
    - `/tmp/java-rust-mixed-membership.YVGEkE/report.json`
  - result:
    - `publish_state_entry_count = 2`
    - `all_first_frame_publish_state = true`
    - `all_no_follow_up_frames = true`
    - `all_response_written = true`
    - `all_same_tick_remote_eof = true`
    - `result = publish_state_arrives_as_single_request_socket_and_peer_closes_same_tick_after_valid_response`
  - 의미:
    - current mixed의 `publish_state`는 reusable `STATE` channel retention으로 보이지 않음
    - 실제 관측 패턴은 one-shot request socket에 가깝고, peer가 valid response 직후 same-tick EOF를 보냄

- 2026-05-03 mixed reusable node channel failure:
  - checker:
    - `tools/check_mixed_no_reusable_node_channel.py`
  - inputs:
    - `/tmp/state-channel-contract.json`
    - `/tmp/java-rust-mixed-membership.YVGEkE/report.json`
  - result:
    - `reusable_state_contract = true`
    - `internal:discovery/request_peers = 48/48 first-frame`
    - `internal:cluster/request_pre_vote = 28/28 first-frame`
    - `internal:coordination/fault_detection/follower_check = 27/27 first-frame`
    - `internal:cluster/coordination/publish_state = 2/2 first-frame`
    - `all_coordinator_actions_arrive_as_connection_first_frame = true`
    - `result = mixed_runtime_never_establishes_reusable_node_channel_so_publication_stays_on_one_shot_sockets`
  - 의미:
    - current mixed의 문제는 `publish_state` 한 액션의 특수 케이스가 아님
    - `transport/handshake` 이후 reusable connected node channel이 성립하지 않아 coordinator/publication path 전체가 one-shot socket으로 남음

- 2026-05-03 connected node registration gap:
  - checker:
    - `tools/check_connected_node_registration_gap.py`
  - inputs:
    - `/tmp/followup-contract.json`
    - `/tmp/current-mixed-followup.json`
    - `/tmp/current-mixed-no-reuse.json`
  - result:
    - `source_full_connect_contract = true`
    - `mixed_followup_failure_cleared = true`
    - `mixed_no_reusable_channel = true`
    - `result = followup_failure_cleared_but_full_connection_promotion_or_registration_still_missing_in_mixed_runtime`
  - 의미:
    - current mixed는 더 이상 old `followup connection failed` 단계에 있지 않음
    - 하지만 reusable connected node channel registration까지는 못 올라가므로, 남은 gap은 `connectToNode` 이후 promotion/registration 경계임

- 2026-05-03 registration boundary break:
  - extractor/checker:
    - `tools/extract_connection_manager_registration_boundary.py`
    - `tools/check_registration_boundary_break.py`
  - inputs:
    - `/tmp/registration-boundary.json`
    - `/tmp/current-mixed-followup.json`
    - `/tmp/current-mixed-no-reuse.json`
  - result:
    - `registration_boundary_present = true`
    - `mixed_followup_failure_cleared = true`
    - `mixed_no_reusable_channel = true`
    - `result = mixed_runtime_breaks_between_followup_acceptance_and_connected_nodes_registration`
  - 의미:
    - current mixed는 `followup acceptance` 이후 coordinator 요청을 실제로 받지만
    - source 기준 reusable connection 승격 지점인 `connectedNodes.putIfAbsent` / `onNodeConnected` 효과는 보이지 않음
    - 다음 남은 질문은 validator/close ordering/socket lifecycle 중 어디서 registration이 무산되는가임

- 2026-05-03 registration gap cause:
  - extractor/checker:
    - `tools/extract_validator_failure_close_contract.py`
    - `tools/check_registration_gap_cause.py`
  - inputs:
    - `/tmp/validator-contract.json`
    - `/tmp/current-mixed-followup.json`
    - `/tmp/current-mixed-no-reuse.json`
    - `/tmp/current-mixed-transport-end.json`
    - `/tmp/current-mixed-transport-window.json`
  - result:
    - `validator_contract_present = true`
    - `mixed_followup_failure_cleared = true`
    - `mixed_no_reusable_channel = true`
    - `identity_response_always_followed_by_remote_eof = true`
    - `followup_channel_closes_sub_threshold = true`
    - `result = socket_lifecycle_or_close_ordering_after_identity_response_is_more_direct_cause_than_validator_failure`
  - 의미:
    - current mixed의 registration gap은 validator mismatch보다는
    - `identity response` 직후 sub-second peer close / socket lifecycle 쪽이 더 직접 원인으로 보임

- 2026-05-03 close ordering trigger instrumentation:
  - runtime instrumentation:
    - `main.rs` transport capture에
      - `hold_open_started_at_ms`
      - `first_post_response_event`
      추가
  - checker:
    - `tools/check_mixed_close_ordering_trigger.py`
  - actual artifact:
    - `/tmp/java-rust-mixed-membership.GETjLw/report.json`
  - result:
    - `publish_state_entry_count = 1`
    - `all_have_hold_open_start = true`
    - `all_first_post_response_event_remote_eof = true`
    - `all_same_tick_close = true`
    - `result = peer_side_remote_eof_is_first_post_response_event_for_every_publish_state_socket`
  - 추가 matrix:
    - `tools/check_mixed_first_post_response_event_matrix.py`
    - `internal:transport/handshake = 27/27 remote_eof`
    - `internal:discovery/request_peers = 49/49 remote_eof`
    - `internal:cluster/request_pre_vote = 26/26 remote_eof`
    - `internal:coordination/fault_detection/follower_check = 26/26 remote_eof`
    - `internal:cluster/coordination/publish_state = 1/1 remote_eof`
    - `result = first_post_response_event_remote_eof_for_every_coordinator_socket`
  - 의미:
    - current mixed의 peer-side close ordering은 특정 action 하나의 예외가 아니라 coordinator/publication socket 전반의 공통 lifecycle 패턴임

- 2026-05-03 action-neutral socket lifecycle matrix:
  - checker:
    - `tools/check_mixed_socket_lifecycle_window_matrix.py`
  - input:
    - `/tmp/java-rust-mixed-membership.GETjLw/report.json`
  - result:
    - `internal:transport/handshake: 707ms~812ms, all_remote_eof=true`
    - `internal:discovery/request_peers: 548ms~810ms, all_remote_eof=true`
    - `internal:cluster/request_pre_vote: 610ms~780ms, all_remote_eof=true`
    - `internal:coordination/fault_detection/follower_check: 425ms~753ms, all_remote_eof=true`
    - `internal:cluster/coordination/publish_state: 0ms, all_remote_eof=true`
    - `result = coordinator_sockets_are_uniform_one_shot_sub_threshold_remote_eof_lifecycle`
  - 의미:
    - current mixed의 문제는 특정 request type이나 payload가 아니라
    - coordinator/publication socket 전반이 `response 1개를 받은 뒤 1초 미만에 닫히는 one-shot lifecycle`로 고정된 점임

- 2026-05-03 openConnection-like mixed lifecycle:
  - extractor/checker:
    - `tools/extract_connection_manager_open_vs_reuse_contract.py`
    - `tools/check_mixed_open_connection_like_lifecycle.py`
  - inputs:
    - `/tmp/open-vs-reuse-contract.json`
    - `/tmp/current-mixed-no-reuse.json`
    - `/tmp/current-mixed-lifecycle-matrix.json`
  - result:
    - `source_open_vs_reuse_contract_present = true`
    - `mixed_no_reusable_channel = true`
    - `mixed_one_shot_lifecycle = true`
    - `result = mixed_runtime_looks_like_repeated_open_connection_without_connected_nodes_reuse`
  - 의미:
    - current mixed는 source가 기대하는 `getConnection(connectedNodes)` reuse 모드가 아니라
    - repeated `openConnection`-like one-shot lifecycle로 보임

- 2026-05-03 repeated connector loop:
  - checker:
    - `tools/check_mixed_repeated_connector_loop.py`
  - inputs:
    - `/tmp/followup-contract.json`
    - `/tmp/java-rust-mixed-membership.GETjLw/report.json`
  - result:
    - `source_connector_contract_present = true`
    - `tcp_handshake_first_frame_count = 53`
    - `transport_handshake_first_frame_count = 27`
    - `request_peers_first_frame_count = 49`
    - `result = mixed_runtime_reenters_handshaking_connector_loop_instead_of_settled_connected_nodes_reuse`
  - 의미:
    - current mixed는 일회성 socket만 많이 여는 수준을 넘어서
    - `HandshakingTransportAddressConnector`/full-connect 시도를 반복하면서도 settled reusable connection으로 넘어가지 못하는 상태임

- 2026-05-03 close-listener unsettle cause:
  - checker:
    - `tools/check_connector_loop_close_listener_cause.py`
  - inputs:
    - `/tmp/registration-boundary.json`
    - `/tmp/current-mixed-connector-loop.json`
    - `/tmp/current-mixed-lifecycle-matrix.json`
  - result:
    - `close_listener_unregisters_connected_node = true`
    - `repeated_connector_loop_present = true`
    - `transport_handshake_short_remote_eof = true`
    - `result = transport_handshake_channel_close_would_immediately_unsettle_any_connected_nodes_registration`
  - 의미:
    - current mixed에서 `transport/handshake` channel이 짧게 닫히는 한
    - source 계약상 어떤 `connectedNodes` registration이 생겨도 close listener가 즉시 제거하게 됨

- 2026-05-03 transport/handshake direct unsettle trigger:
  - checker:
    - `tools/check_transport_handshake_unsettle_trigger.py`
  - inputs:
    - `/tmp/registration-boundary.json`
    - `/tmp/java-rust-mixed-membership.GETjLw/report.json`
  - result:
    - `close_listener_unregisters_connected_node = true`
    - `transport_handshake_first_frame_count = 27`
    - `all_identity_response_then_remote_eof = true`
    - `result = transport_handshake_identity_response_then_remote_eof_is_direct_unsettle_trigger_for_any_connected_nodes_registration`
  - 의미:
    - current mixed에서 any `connectedNodes` registration을 무너뜨리는 직접 trigger는
    - valid `transport/handshake` identity response 뒤 peer가 곧바로 보내는 `remote_eof`임

- 2026-05-03 transport/handshake probe-close expectation:
  - checker:
    - `tools/check_transport_handshake_probe_close_expectation.py`
  - inputs:
    - `/tmp/followup-contract.json`
    - `/tmp/java-rust-mixed-membership.GETjLw/report.json`
  - result:
    - `source_probe_close_expected = true`
    - `transport_handshake_first_frame_count = 27`
    - `all_identity_then_remote_eof = true`
    - `result = transport_handshake_remote_eof_matches_expected_probe_close_before_full_connect`
  - 의미:
    - `transport/handshake` 뒤 `remote_eof` 자체는 current mixed의 이상 행동이라기보다
    - source가 기대하는 probe-close와 정렬됨
    - 따라서 남은 gap은 probe-close 이후 이어져야 할 full connect / settled reuse가 왜 성립하지 않는가임

- 2026-05-03 full connect never settles:
  - checker:
    - `tools/check_full_connect_never_settles.py`
  - inputs:
    - `/tmp/followup-contract.json`
    - `/tmp/current-mixed-no-reuse.json`
    - `/tmp/java-rust-mixed-membership.GETjLw/report.json`
  - result:
    - `source_full_connect_after_probe = true`
    - `mixed_no_connected_reuse = true`
    - `transport_handshake_first_frame_count = 27`
    - `result = full_connect_is_retried_repeatedly_but_never_settles_into_connected_nodes_reuse`
  - 의미:
    - current mixed의 핵심 문제는 probe-close 자체가 아니라
    - probe-close 뒤 이어져야 할 full connect가 매번 재시도되면서도 settled reusable connection으로 수렴하지 않는 점임

- 2026-05-03 direct vs mixed full-connect settle gap:
  - checker:
    - `tools/check_direct_vs_mixed_full_connect_settle_gap.py`
  - inputs:
    - `/tmp/java-java-trace.latest.check.json`
    - `/tmp/current-mixed-full-connect.json`
  - result:
    - `direct_publish_state_count = 24`
    - `direct_commit_state_count = 24`
    - `mixed_transport_handshake_first_frame_count = 27`
    - `mixed_result = full_connect_is_retried_repeatedly_but_never_settles_into_connected_nodes_reuse`
    - `result = direct_reference_settles_after_handshake_while_mixed_retries_full_connect_without_settling`
  - 의미:
    - direct Java-Java reference는 handshake 이후 publish/commit으로 정상 수렴
    - current mixed만 full-connect retry loop에 머물러 있음

- 2026-05-03 Rust vs Java ephemeral_id gap:
  - extractor/checker:
    - `tools/extract_rust_transport_identity_contract.py`
    - `tools/check_java_vs_rust_ephemeral_id_gap.py`
  - inputs:
    - `/tmp/rust-transport-identity-contract.json`
    - `/tmp/java-rust-mixed-membership.GETjLw/report.json`
  - result:
    - `java_reference_has_distinct_ephemeral_id = true`
    - `rust_reuses_node_id_as_ephemeral_id = true`
    - `result = rust_transport_identity_reuses_node_id_as_ephemeral_id_unlike_java_reference`
  - 의미:
    - current mixed의 full-connect settle failure와 직접 연결될 수 있는 concrete wire delta 하나는
    - Rust transport identity가 Java reference와 달리 `ephemeral_id`를 별도 값으로 두지 않는 점임

- 2026-05-03 distinct ephemeral_id probe:
  - implementation:
    - `main.rs`의 `DevTransportIdentity`에 `ephemeral_id` 추가
    - `transport/handshake` response와 local publish/join helper path가 distinct `ephemeral_id`를 사용하도록 수정
  - actual probe:
    - `/tmp/java-rust-mixed-membership.jINFlY/report.json`
  - post-change checks:
    - `rust_reuses_node_id_as_ephemeral_id = false`
    - `transport_handshake_first_frame_count = 26`
    - `result = full_connect_is_retried_repeatedly_but_never_settles_into_connected_nodes_reuse`
  - 의미:
    - `ephemeral_id`를 Java-style로 분리해도 current mixed의 full-connect settle failure는 해소되지 않음
    - 따라서 이 차이는 root cause 단독 설명으로는 부족함

- 2026-05-03 full local DiscoveryNode distinct ephemeral_id rerun:
  - correction:
    - earlier `jINFlY` run 뒤 코드 재확인 결과, local `publish_with_join_response`와 outbound `join`의 `write_discovery_node_wire(...)` 2곳은 아직 `node_id`를 `ephemeral_id`로 재사용하고 있었음
    - 이번 회차에서 그 2곳까지 `transport_identity.ephemeral_id`로 수정
  - actual probe:
    - `/tmp/java-rust-mixed-membership.cVRuiJ/report.json`
  - post-change checks:
    - `/tmp/rust-transport-identity-contract.json`
    - `transport_identity_response_reuses_node_id_as_ephemeral_id = false`
    - `publish_with_join_response_reuses_node_id_as_ephemeral_id = false`
    - `rust_reuses_node_id_as_ephemeral_id = false`
    - `result = rust_identity_ephemeral_gap_not_detected`
    - `all_coordinator_actions_arrive_as_connection_first_frame = true`
    - `result = full_connect_is_retried_repeatedly_but_never_settles_into_connected_nodes_reuse`
  - 의미:
    - 이제 Rust 쪽 local `DiscoveryNode.ephemeral_id` 재사용 차이는 `transport/handshake`, local publish response, outbound join 모두에서 제거됨
    - 그래도 current mixed는 여전히 repeated full-connect retry / no connectedNodes reuse 상태이므로, 다음 후보는 다른 wire/runtime 차이여야 함

- 2026-05-03 next DiscoveryNode payload gap after distinct ephemeral_id:
  - checker:
    - `tools/check_java_vs_rust_discovery_node_payload_gap.py`
  - inputs:
    - `crates/os-node/src/main.rs`
    - `/tmp/java-rust-mixed-membership.cVRuiJ/report.json`
  - result:
    - `rust_writer_hardcodes_empty_attributes = true`
    - `rust_supports_remote_cluster_client_wire_role = true`
    - `java_reference_roles = [cluster_manager, data, ingest, remote_cluster_client]`
    - `rust_local_roles = [cluster_manager, data, ingest]`
    - `result = rust_local_discovery_node_omits_remote_cluster_client_and_attributes_unlike_java_reference`
  - 의미:
    - `ephemeral_id` 차이를 제거한 뒤 남는 첫 concrete payload delta는
    - Rust local `DiscoveryNode`가 Java reference와 달리 `remote_cluster_client` role을 싣지 않고 node attributes도 비운다는 점임

- 2026-05-03 remote_cluster_client role actual mixed probe:
  - correction:
    - `tools/run-steelsearch-dev.sh`가 `--node.roles "${STEELSEARCH_NODE_ROLES:-cluster_manager,data,ingest}"`로 explicit override하고 있어서, initial default role 변경만으로는 mixed probe runtime에 `remote_cluster_client`가 반영되지 않았음
    - 이번 회차에서 launcher default도 `cluster_manager,data,ingest,remote_cluster_client`로 맞춤
  - actual probe:
    - `/tmp/java-rust-mixed-membership.nsVJlS/report.json`
  - post-change checks:
    - `rust_local_roles = [cluster_manager, data, ingest, remote_cluster_client]`
    - `result = no_concrete_discovery_node_payload_gap_detected`
    - `transport/handshake` response `message_length = 207` (`182 -> 207`)
    - `result = full_connect_is_retried_repeatedly_but_never_settles_into_connected_nodes_reuse`
  - interpretation:
    - local Rust `DiscoveryNode`의 missing `remote_cluster_client` role은 actual mixed runtime에서 제거됐지만 settle failure는 그대로임
    - 따라서 남는 concrete payload delta는 node attributes empty-map 쪽이 더 유력함
  - unclear point:
    - `/tmp/java-rust-mixed-membership.nsVJlS/report.json`에서 `internal:cluster/request_pre_vote`에 `post_follow_up_frame_count = 1`이 한 번 관측되어 기존의 “all coordinator actions are first-frame one-shot” 패턴과 약간 달라짐
    - 다만 전체 결과는 여전히 `full_connect_is_retried_repeatedly_but_never_settles_into_connected_nodes_reuse`

- 2026-05-03 local DiscoveryNode attributes actual mixed probe:
  - implementation:
    - `DevTransportIdentity.attributes` 추가
    - local Rust `DiscoveryNode`에 최소 attribute `shard_indexing_pressure_enabled=true` 추가
    - `write_discovery_node_wire(...)`가 attributes map을 실제 직렬화하도록 수정
    - `build_transport_handshake_identity_response(...)`도 같은 attributes map을 쓰도록 수정
  - actual probe:
    - `/tmp/java-rust-mixed-membership.lN9fNo/report.json`
  - post-change checks:
    - `rust_writer_hardcodes_empty_attributes = false`
    - `rust_local_roles = [cluster_manager, data, ingest, remote_cluster_client]`
    - `result = no_concrete_discovery_node_payload_gap_detected`
    - `internal:transport/handshake response message_length = 244`
    - `result = full_connect_is_retried_repeatedly_but_never_settles_into_connected_nodes_reuse`
  - 의미:
    - local Rust `DiscoveryNode`의 role/attributes payload는 이제 Java reference와의 가장 직접적인 delta가 제거됨
    - 그래도 mixed path는 여전히 full-connect settle로 안 가므로, 다음 후보는 payload가 아니라 non-payload wire/runtime 차이여야 함

- 2026-05-03 post-payload non-profile candidate:
  - checker:
    - `tools/check_post_payload_channel_profile_gap.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/ConnectionProfile.java`
    - `/tmp/java-rust-mixed-membership.lN9fNo/report.json`
  - result:
    - `source_has_single_channel_profile = true`
    - `source_has_default_multi_channel_profile = true`
    - `transport_handshake_count = 29`
    - `transport_handshake_first_frame_only = 29`
    - `request_peers_count = 48`
    - `request_peers_first_frame_only = 48`
    - `result = payload_corrected_but_mixed_runtime_still_looks_like_single_use_connection_profile_instead_of_default_multi_channel_profile`
  - 의미:
    - role/attributes payload를 Java reference 쪽에 맞춘 뒤에도 mixed runtime은 source의 settled default multi-channel node profile로 가지 않음
    - 다음 남은 gap은 payload가 아니라, `connectToNode` 이후 왜 default multi-channel profile로 승격/유지되지 못하고 single-use connection profile처럼 머무는가임

- 2026-05-03 post-payload connectedNodes reuse gap:
  - checker:
    - `tools/check_post_payload_connected_nodes_reuse_gap.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TransportService.java`
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/ClusterConnectionManager.java`
    - `/tmp/java-rust-mixed-membership.lN9fNo/report.json`
  - result:
    - `source_send_request_uses_get_connection = true`
    - `source_has_connected_nodes_registration = true`
    - `internal:coordination/fault_detection/follower_check = 28/28 first-frame-only`
    - `internal:cluster/coordination/publish_state = 2/2 first-frame-only`
    - `result = post_payload_corrected_runtime_still_never_reaches_connected_nodes_reuse_for_late_coordinator_actions`
  - 의미:
    - payload를 맞춘 뒤에도 current mixed runtime은 late coordinator actions조차 `connectedNodes` reuse path로 보내지 못함
    - 다음 남은 gap은 generic payload/profile이 아니라, `TransportService.getConnection(node)` / `connectedNodes` settled registration 경계 자체임

- 2026-05-03 late action nodeConnected/getConnection reuse gap:
  - checker:
    - `tools/check_late_action_node_connected_gap.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TransportService.java`
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/ClusterConnectionManager.java`
    - `/tmp/java-rust-mixed-membership.lN9fNo/report.json`
  - result:
    - `source_send_request_fails_if_not_connected = true`
    - `source_node_connected_is_connected_nodes_contains = true`
    - `transport_handshake_first_frame_count = 29`
    - `late_action_counts = { publish_state: 2, follower_check: 28 }`
    - `late_actions_all_first_frame_only = true`
    - `result = late_actions_still_arrive_on_new_sockets_so_current_mixed_runtime_never_reaches_nodeConnected_getConnection_reuse`
  - 의미:
    - corrected payload 이후에도 current mixed는 `nodeConnected(node)`가 true인 settled state로 못 올라감
    - 따라서 다음 남은 질문은 “payload mismatch냐”가 아니라 “왜 connectedNodes settled registration이 성립하지 않아 late actions까지 새 socket으로만 오느냐”임

- 2026-05-03 post-payload transport/handshake unsettle trigger:
  - checker:
    - `tools/check_post_payload_transport_handshake_unsettle.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/ClusterConnectionManager.java`
    - `/tmp/java-rust-mixed-membership.lN9fNo/report.json`
  - result:
    - `source_close_listener_unregisters = true`
    - `transport_handshake_count = 29`
    - `all_identity_response_then_remote_eof = true`
    - `result = post_payload_corrected_transport_handshake_channels_still_close_immediately_so_any_provisional_connectedNodes_registration_would_be_unsettled`
  - 의미:
    - corrected payload 이후에도 full-connect용 `transport/handshake` socket이 살아남지 못함
    - 그래서 설령 provisional `connectedNodes.putIfAbsent(...)`가 잠깐 있었더라도 close-listener contract로 바로 unsettle될 조건임

- 2026-05-03 transport/handshake socket class split:
  - checker:
    - `tools/check_transport_handshake_socket_classes.py`
  - input:
    - `/tmp/java-rust-mixed-membership.lN9fNo/report.json`
  - result:
    - `probe_upgrade_socket_count = 28`
    - `direct_full_connect_transport_handshake_socket_count = 29`
    - `direct_full_connect_all_remote_eof = true`
    - `result = problematic_class_is_direct_full_connect_transport_handshake_socket_that_remote_eof_closes_after_identity_response`
  - 의미:
    - 문제를 일으키는 socket class는 generic probe-upgrade socket이 아니라
    - `first-frame = internal:transport/handshake`로 시작하는 direct full-connect socket임

- 2026-05-03 transport/handshake identity equivalence:
  - checker:
    - `tools/check_transport_handshake_identity_equivalence.py`
  - input:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `probe_identity_variant_count = 1`
    - `direct_identity_variant_count = 1`
    - `responses_equivalent = true`
    - `result = probe_upgrade_and_direct_full_connect_transport_handshake_identity_responses_are_byte_identical`
  - 의미:
    - Java peer가 direct full-connect socket을 닫는 이유는
    - probe-upgrade와 direct full-connect 사이의 `transport/handshake` identity payload 차이로는 설명되지 않음

- 2026-05-03 validator mismatch after identity equivalence:
  - checker:
    - `tools/check_validator_mismatch_after_equivalent_identity.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TransportService.java`
    - `/tmp/transport-handshake-identity-equivalence.json`
  - result:
    - `source_validator_checks_node_equals_remote = true`
    - `identity_equivalent = true`
    - `result = validator_mismatch_is_not_supported_by_artifact_once_probe_and_direct_transport_handshake_identities_are_equivalent`
  - 의미:
    - current mixed의 direct full-connect socket close는
    - `transport/handshake` identity mismatch나 validator mismatch로는 설명되지 않음
    - 다음 초점은 post-handshake non-identity trigger임

- 2026-05-03 direct full-connect pre-second-frame close:
  - checker:
    - `tools/check_direct_full_connect_pre_second_frame_close.py`
  - inputs:
    - `/tmp/validator-after-identity.json`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `validator_ruled_out = true`
    - `direct_full_connect_socket_count = 27`
    - `all_no_follow_up_frame = true`
    - `all_no_post_follow_up_frame = true`
    - `all_remote_eof_first_post_event = true`
    - `all_identity_response_then_remote_eof = true`
    - `result = direct_full_connect_socket_closes_before_any_second_frame_so_next_gap_is_pre_second_frame_non_identity_trigger`
  - 의미:
    - current mixed의 direct full-connect `transport/handshake` socket close는
    - validator/identity mismatch 이후의 일반적인 late-action failure가 아니라
    - 두 번째 frame 전 단계에서 일어나는 non-identity close trigger로 더 좁혀짐

- 2026-05-03 direct full-connect hold-open peer close:
  - checker:
    - `tools/check_direct_full_connect_hold_open_peer_close.py`
  - input:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `direct_full_connect_socket_count = 27`
    - `all_hold_open_started = true`
    - `all_no_follow_up_or_post = true`
    - `all_remote_eof_first_post = true`
    - `all_peer_closed_after_local_hold_open = true`
    - `result = direct_full_connect_socket_enters_local_hold_open_but_peer_still_closes_before_any_post_handshake_request`
  - 의미:
    - current mixed의 direct full-connect `transport/handshake` socket close는
    - local immediate close가 아니라 local hold-open 이후 peer-side close임
    - 그리고 close 시점은 어떤 post-handshake request decode 이전임

- 2026-05-03 direct full-connect profile promotion gap:
  - checker:
    - `tools/check_direct_full_connect_profile_promotion_gap.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/ConnectionProfile.java`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `source_has_default_multi_channel_profile = true`
    - `direct_full_connect_socket_count = 27`
    - `all_no_follow_up_or_post = true`
    - `all_remote_eof_first_post = true`
    - `all_hold_open_started = true`
    - `result = direct_full_connect_sockets_close_before_default_multi_channel_profile_promotion_or_reuse`
  - 의미:
    - current mixed의 direct full-connect `transport/handshake` socket close는
    - default multi-channel profile 승격/재사용 이후의 action-level 문제가 아니라
    - 그 직전 단계에서 발생하는 peer-side close trigger로 더 좁혀짐

- 2026-05-03 direct full-connect close restart loop:
  - checker:
    - `tools/check_direct_full_connect_close_restarts_fresh_socket_loop.py`
  - input:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `direct_full_connect_socket_count = 27`
    - `all_remote_eof = true`
    - `restart_count = 26`
    - `all_restart_into_fresh_socket_loop = false`
    - `result = direct_full_connect_restart_loop_not_fully_established`
  - 의미:
    - direct full-connect close 뒤 fresh-socket loop 재진입은 거의 전부 관측되지만
    - 마지막 1건은 capture tail인지 별도 종료 path인지 아직 불명확함

- 2026-05-03 direct full-connect restart tail case:
  - checker:
    - `tools/check_direct_full_connect_restart_tail_case.py`
  - input:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `direct_full_connect_socket_count = 27`
    - `non_restart_count = 1`
    - `terminal_tail_case = false`
    - `result = non_restart_direct_full_connect_socket_not_explained_as_terminal_tail`
  - 의미:
    - `26/27` 재진입 패턴의 마지막 1건은 단순 capture tail이 아님
    - 별도 종료 path 또는 예외적 socket lifecycle 가능성이 남음

- 2026-05-03 profile promotion close outcomes:
  - checker:
    - `tools/check_profile_promotion_close_outcomes.py`
  - inputs:
    - `/tmp/profile-promotion-gap.json`
    - `/tmp/direct-full-connect-tail-case.json`
  - result:
    - `promotion_gap_established = true`
    - `direct_full_connect_socket_count = 27`
    - `non_restart_count = 1`
    - `exception_not_tail = true`
    - `result = profile_promotion_pre_reuse_peer_close_trigger_established_with_dominant_restart_loop_and_one_non_tail_exception`
  - 의미:
    - current mixed의 direct full-connect close는
    - source default multi-channel profile 승격/재사용 직전의 peer-side close trigger로 고정됨
    - 그리고 outcome은 `26/27 fresh-socket restart loop`와 `1/27 non-tail exception path`로 갈라짐

- 2026-05-03 direct full-connect close path split:
  - extractor:
    - `tools/extract_direct_full_connect_close_paths.py`
  - input:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `direct_full_connect_socket_count = 27`
    - `restart_loop_count = 26`
    - `exception_path_count = 1`
    - `exception_entries[0].peer_addr = 127.0.0.1:46180`
    - `exception_entries[0].connection_started_at_ms = 1777819495994`
    - `exception_entries[0].connection_end_at_ms = 1777819496817`
    - `exception_entries[0].connection_end = remote_eof`
  - 의미:
    - profile-promotion 직전 peer-side close trigger는 artifact 상에서
    - `26건 restart loop`와 `1건 exception socket`으로 실제 분리 가능해짐

- 2026-05-03 restart loop next action pattern:
  - checker:
    - `tools/check_restart_loop_next_action_pattern.py`
  - input:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `restart_observation_count = 27`
    - `next_action_counts = { internal:tcp/handshake: 27 }`
    - `dominant_next_action = internal:tcp/handshake`
    - `dominant_next_action_count = 27`
  - 의미:
    - direct full-connect close 뒤 restart loop path는 예외 없이 다시 `internal:tcp/handshake`로 재진입함
    - 즉 current mixed는 settled reuse가 아니라 connector probe 단계로 반복 복귀함

- 2026-05-03 restart loop reenters connector probe:
  - checker:
    - `tools/check_restart_loop_reenters_connector_probe.py`
  - inputs:
    - `/tmp/followup-contract.json`
    - `/tmp/restart-next-action.json`
  - result:
    - `source_connector_probe_contract = true`
    - `restart_observation_count = 27`
    - `restarts_to_tcp_handshake = true`
    - `result = restart_loop_reenters_handshaking_transport_address_connector_probe_entrypoint`
  - 의미:
    - current mixed의 dominant restart path는
    - settled `connectedNodes` reuse가 아니라 `HandshakingTransportAddressConnector` probe entrypoint로 되돌아가는 loop임

- 2026-05-03 probe reentry caused by unsettled connectedNodes:
  - checker:
    - `tools/check_probe_reentry_caused_by_unsettled_connected_nodes.py`
  - inputs:
    - `/tmp/registration-boundary.json`
    - `/tmp/probe-reentry.json`
  - result:
    - `source_close_listener_unregisters = true`
    - `dominant_path_reenters_probe = true`
    - `result = dominant_restart_path_reenters_probe_because_connection_close_prevents_settled_connected_nodes_reuse`
  - 의미:
    - current mixed의 dominant path는
    - connection close 때문에 settled `connectedNodes` reuse가 성립하지 못해
    - `HandshakingTransportAddressConnector` probe entrypoint로 복귀함

- 2026-05-03 direct full-connect close window:
  - checker:
    - `tools/check_direct_full_connect_close_window.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `1000`
  - result:
    - `window_count = 27`
    - `min_window_ms = 691`
    - `max_window_ms = 804`
    - `all_sub_threshold = true`
    - `result = direct_full_connect_peer_close_has_consistent_sub_threshold_window`
  - 의미:
    - current mixed의 dominant path에서 peer-side close trigger는 무작위가 아니라
    - `691ms~804ms`의 일관된 sub-second delayed abort window를 가짐

- 2026-05-03 close window timeout scale:
  - checker:
    - `tools/check_close_window_timeout_scale.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/HandshakingTransportAddressConnector.java`
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/common/network/NetworkService.java`
    - `/tmp/direct-full-connect-close-window.json`
  - result:
    - `probe_handshake_timeout_ms = 1000`
    - `transport_connect_timeout_ms = 30000`
    - `max_window_ms = 804`
    - `result = observed_peer_close_window_matches_probe_handshake_timeout_scale_not_transport_connect_timeout_scale`
  - 의미:
    - dominant path의 delayed abort는 `30s transport connect timeout` scale이 아니라
    - `1s discovery.probe.handshake_timeout` scale과 더 가깝다

- 2026-05-03 abort to probe retry gap:
  - checker:
    - `tools/check_abort_to_probe_retry_gap.py`
  - input:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `gap_count = 27`
    - `min_gap_ms = 6`
    - `max_gap_ms = 17627`
    - `all_immediate_le_5ms = false`
    - `result = abort_to_probe_retry_gap_not_immediate_or_not_fully_observed`
  - 의미:
    - dominant path의 `abort -> tcp/handshake retry`는 즉시 재시도가 아님
    - retry gap이 넓게 퍼져 있어서 다음부터는 가변 지연을 가진 probe-timeout-scale retry로 다뤄야 함

- 2026-05-03 discovery scheduler scale candidate:
  - checker:
    - `tools/check_discovery_scheduler_scale_candidate.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/HandshakingTransportAddressConnector.java`
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/direct-full-connect-close-window.json`
  - result:
    - `probe_handshake_timeout_ms = 1000`
    - `find_peers_interval_ms = 1000`
    - `request_peers_timeout_ms = 3000`
    - `observed_max_window_ms = 804`
    - `result = discovery_scheduler_1s_scale_is_more_plausible_next_candidate_than_transport_connect_timeout_scale`
  - 의미:
    - dominant path의 `1s` scale abort/retry는
    - `30s transport connect timeout`보다 `PeerFinder.find_peers_interval=1s`와 `probe.handshake_timeout=1s` 축이 더 유력한 다음 source 후보임

- 2026-05-03 probe retry 1s tick alignment:
  - checker:
    - `tools/check_probe_retry_1s_tick_alignment.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `250`
  - result:
    - `gap_count = 27`
    - `aligned_count = 26`
    - `tick_buckets = { 0: 26, 18: 1 }`
    - `result = probe_retry_gaps_do_not_uniformly_align_to_1s_ticks`
  - 의미:
    - dominant path의 retry gap은 균일한 `1s` cadence가 아님
    - 오히려 `26건`은 거의 즉시 재진입이고 `1건`만 긴 outlier라서
    - discovery scheduler 후보는 uniform cadence가 아니라 mixed path split으로 다시 봐야 함

- 2026-05-03 discovery scheduler candidate validation:
  - checker:
    - `tools/check_discovery_scheduler_candidate_validation.py`
  - inputs:
    - `/tmp/discovery-scheduler-scale.json`
    - `/tmp/probe-retry-1s-alignment.json`
  - result:
    - `source_scheduler_candidate_present = true`
    - `artifact_rejects_uniform_1s_cadence = true`
    - `result = discovery_scheduler_candidate_validated_but_uniform_1s_cadence_not_supported_by_artifact`
  - 의미:
    - source에는 `1s` discovery scheduler 후보가 있지만
    - actual mixed artifact는 uniform `1s` cadence를 지지하지 않음
    - 따라서 다음부터는 `26/27 immediate-ish + 1/27 long-gap` split 자체를 원인 후보로 더 파야 함

- 2026-05-03 probe retry gap paths:
  - extractor:
    - `tools/extract_probe_retry_gap_paths.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `250`
  - result:
    - `immediate_count = 26`
    - `delayed_count = 1`
    - `delayed_entries[0].peer_addr = 127.0.0.1:46180`
    - `delayed_entries[0].gap_ms = 17627`
  - 의미:
    - dominant retry path는 `26건 immediate-ish`
    - delayed retry path는 `1건 17627ms outlier`
    - 다음부터는 두 path를 source/runtime 관점에서 분리해서 봐야 함

- 2026-05-03 retry gap paths vs close paths mapping:
  - checker:
    - `tools/check_retry_gap_paths_vs_close_paths.py`
  - inputs:
    - `/tmp/probe-retry-gap-paths.json`
    - `/tmp/direct-full-connect-close-paths.json`
  - result:
    - `immediate_matches_restart_loop_count = true`
    - `delayed_peer_matches_exception_peer = true`
    - `delayed_peer = 127.0.0.1:46180`
    - `exception_peer = 127.0.0.1:46180`
    - `result = retry_gap_split_maps_cleanly_to_restart_loop_vs_exception_close_paths`
  - 의미:
    - `26건 immediate-ish retry`는 restart loop path와 clean mapping됨
    - `1건 17627ms long-gap`은 direct full-connect close의 exception socket path와 같은 경로임

- 2026-05-03 long-gap exception election scale:
  - checker:
    - `tools/check_long_gap_exception_election_scale.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/ElectionSchedulerFactory.java`
    - `/tmp/probe-retry-gap-paths.json`
  - result:
    - `election_initial_timeout_ms = 100`
    - `election_backoff_ms = 100`
    - `election_max_timeout_ms = 10000`
    - `election_duration_ms = 100`
    - `delayed_gap_ms = 17627`
    - `result = long_gap_exception_is_more_consistent_with_election_scheduler_scale_than_1s_probe_scale`
  - 의미:
    - `1/27 17627ms long-gap` exception path는
    - `1s probe` cadence보다 election/coordination scheduler scale과 더 잘 맞음

- 2026-05-03 long-gap multi-round election scheduler scale:
  - checker:
    - `tools/check_long_gap_multi_round_election_scheduler.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/ElectionSchedulerFactory.java`
    - `/tmp/probe-retry-gap-paths.json`
  - result:
    - `election_max_timeout_ms = 10000`
    - `election_duration_ms = 100`
    - `single_round_upper_bound_ms = 10100`
    - `delayed_gap_ms = 17627`
    - `result = long_gap_exception_fits_multi_round_election_scheduler_scale_better_than_single_round_or_1s_probe`
  - 의미:
    - `17627ms` long-gap exception path는
    - `1s probe`나 single-round election window보다
    - multi-round election scheduler scale과 더 잘 맞음

- 2026-05-03 long-gap minimum election rounds:
  - checker:
    - `tools/check_long_gap_min_election_rounds.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/ElectionSchedulerFactory.java`
    - `/tmp/probe-retry-gap-paths.json`
  - result:
    - `round_upper_bound_ms = 10100`
    - `delayed_gap_ms = 17627`
    - `min_rounds = 2`
    - `result = long_gap_exception_requires_at_least_two_election_scheduler_rounds`
  - 의미:
    - `17627ms` long-gap exception path는
    - single-round election jitter가 아니라
    - 최소 `2` rounds 이상의 election/coordination retry 경로가 필요함

- 2026-05-03 long-gap retry uses new peer socket:
  - checker:
    - `tools/check_long_gap_retries_on_new_peer_socket.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `127.0.0.1:46180`
  - result:
    - `exception_peer_addr = 127.0.0.1:46180`
    - `next_tcp_peer_addr = 127.0.0.1:45884`
    - `next_tcp_started_at_ms = 1777819514444`
    - `retries_on_new_peer_socket = true`
    - `result = long_gap_exception_retries_via_new_peer_socket`
  - 의미:
    - long-gap exception path는
    - 같은 socket continuation이 아니라 multi-round coordination 이후 새 peer socket의 `tcp/handshake` retry로 이어짐

- 2026-05-03 long-gap retry sequence:
  - extractor:
    - `tools/extract_long_gap_retry_sequence.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `1777819496817`
  - result:
    - `sequence_count = 1`
    - `sequence[0].peer_addr = 127.0.0.1:45884`
    - `sequence[0].first_action = internal:tcp/handshake`
    - `sequence[0].follow_up_action = null`
  - 의미:
    - long-gap exception path는 current artifact에서
    - 새 peer socket의 `tcp/handshake` retry까지는 보이지만
    - 그 뒤 follow-up은 capture에 남아 있지 않음

- 2026-05-03 long-gap retry capture tail:
  - checker:
    - `tools/check_long_gap_retry_is_capture_tail.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `127.0.0.1:45884`
  - result:
    - `last_entry_peer_addr = 127.0.0.1:45884`
    - `last_entry_first_action = internal:tcp/handshake`
    - `is_capture_tail = true`
    - `result = long_gap_retry_sequence_is_capture_tail`
  - 의미:
    - long-gap exception 뒤 새 peer socket `tcp/handshake`만 보이는 이유는
    - isolated path라서가 아니라 current artifact가 그 지점에서 끝났기 때문임

- 2026-05-03 pre-exception request_peers burst:
  - extractor/checker:
    - `tools/extract_pre_exception_sequence.py`
    - `tools/check_pre_exception_request_peers_burst.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `1777819495994`
  - result:
    - `request_peers_count = 3`
    - `tcp_handshake_count = 2`
    - `request_peers_same_ms_burst = true`
    - `result = exception_path_is_preceded_by_request_peers_burst_with_concurrent_tcp_handshake`
  - 의미:
    - long-gap exception path 직전 trigger는
    - 순수 election timer만이 아니라 `request_peers` burst와 concurrent `tcp/handshake`를 포함한 discovery round 쪽에 더 가까움

- 2026-05-03 pre-exception burst matches PeerFinder fan-out:
  - checker:
    - `tools/check_pre_exception_burst_matches_peerfinder_fanout.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/pre-exception-sequence.json`
  - result:
    - `source_peerfinder_fanout = true`
    - `request_peers_count = 3`
    - `tcp_handshake_count = 2`
    - `request_peers_same_ms_burst = true`
    - `result = pre_exception_request_peers_burst_is_consistent_with_peerfinder_fanout_round`
  - 의미:
    - long-gap exception path 직전 burst는
    - election timer 단독보다 `PeerFinder`의 `request_peers -> startProbe fan-out` discovery round와 더 잘 맞음

- 2026-05-03 exception socket belongs to same fan-out round:
  - checker:
    - `tools/check_exception_socket_belongs_to_fanout_round.py`
  - inputs:
    - `/tmp/pre-exception-sequence.json`
    - `1777819495994`
    - `1`
  - result:
    - `same_round_entry_count = 4`
    - `same_round_request_peers_count = 3`
    - `same_round_tcp_handshake_count = 1`
    - `result = exception_socket_start_time_belongs_to_same_discovery_fanout_round_as_request_peers_burst`
  - 의미:
    - long-gap exception socket start 자체도
    - `request_peers` burst와 같은 `PeerFinder` discovery fan-out round 안에 있음

- 2026-05-03 exception socket role in fan-out round:
  - checker:
    - `tools/check_exception_socket_role_in_fanout_round.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `1777819495994`
    - `1`
  - result:
    - `same_round_count = 7`
    - `same_round_tcp_count = 1`
    - `same_round_request_peers_count = 3`
    - `same_round_direct_full_connect_count = 1`
    - `result = exception_socket_is_unique_direct_full_connect_member_inside_same_peerfinder_fanout_round`
  - 의미:
    - long-gap exception socket은
    - 같은 `PeerFinder` fan-out round 안에서 유일한 direct full-connect member임

- 2026-05-03 exception member is unique full-connect path:
  - checker:
    - `tools/check_exception_member_is_unique_full_connect_path.py`
  - inputs:
    - `/tmp/followup-contract.json`
    - `/tmp/exception-round-role.json`
  - result:
    - `source_has_full_connect_after_probe = true`
    - `artifact_has_unique_direct_full_connect_member = true`
    - `result = exception_socket_is_unique_full_connect_promotion_member_inside_peerfinder_round`
  - 의미:
    - long-gap exception socket은
    - 같은 `PeerFinder` round 안에서 유일하게 `full-connect promotion` 경로를 타는 member임

- 2026-05-03 exception full-connect failure branch:
  - checker:
    - `tools/check_exception_full_connect_failure_branch.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/exception-round-role.json`
  - result:
    - `source_has_connecting_peer_failure_remove = true`
    - `source_request_peers_failure_only_clears_inflight = true`
    - `artifact_has_unique_full_connect_member = true`
    - `result = exception_member_is_only_round_member_on_connecting_peer_failure_remove_branch`
  - 의미:
    - long-gap exception member만
    - 같은 `PeerFinder` round 안에서 `connecting peer failure -> peersByAddress.remove` branch를 타는 member임

- 2026-05-03 remove branch retries on future wakeup:
  - checker:
    - `tools/check_remove_branch_retries_on_future_wakeup.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/probe-retry-gap-paths.json`
  - result:
    - `source_remove_branch_retries_via_future_wakeup = true`
    - `find_peers_interval_ms = 1000`
    - `delayed_gap_ms = 17627`
    - `result = remove_branch_long_gap_is_consistent_with_retry_on_future_peerfinder_wakeup_rounds`
  - 의미:
    - exception member의 `peersByAddress.remove` branch는
    - same round continuation이 아니라 future `PeerFinder wakeup` rounds를 거쳐 retry되는 경로와 일치함

- 2026-05-03 long-gap minimum PeerFinder wakeups:
  - checker:
    - `tools/check_long_gap_min_peerfinder_wakeups.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/probe-retry-gap-paths.json`
  - result:
    - `find_peers_interval_ms = 1000`
    - `delayed_gap_ms = 17627`
    - `min_wakeups = 18`
    - `result = long_gap_exception_requires_many_peerfinder_wakeup_rounds`
  - 의미:
    - `17627ms` long-gap exception path는
    - single wakeup delay가 아니라 최소 `18` rounds 이상의 `PeerFinder wakeup` 누적 경로를 필요로 함

- 2026-05-03 long-gap singleton reason:
  - checker:
    - `tools/check_long_gap_singleton_reason.py`
  - inputs:
    - `/tmp/probe-retry-gap-paths.json`
    - `/tmp/exception-round-role.json`
  - result:
    - `delayed_count = 1`
    - `same_round_direct_full_connect_count = 1`
    - `same_round_request_peers_count = 3`
    - `result = long_gap_many_round_path_is_singleton_because_same_fanout_round_has_only_one_full_connect_promotion_member`
  - 의미:
    - many-round long-gap path가 `1건`뿐인 이유는
    - 같은 fan-out round 안의 full-connect promotion member가 `1개`뿐이기 때문임

- 2026-05-03 singleton promotion member remove branch mapping:
  - checker:
    - `tools/check_singleton_promotion_member_remove_branch.py`
  - inputs:
    - `/tmp/exception-full-connect-path.json`
    - `/tmp/exception-failure-branch.json`
  - result:
    - `singleton_promotion_member = true`
    - `singleton_remove_branch_member = true`
    - `result = singleton_full_connect_promotion_member_is_same_member_that_takes_remove_branch`
  - 의미:
    - long-gap singleton promotion member와
    - remove branch를 타는 member가 동일함

- 2026-05-03 singleton remove branch remote_eof trigger:
  - checker:
    - `tools/check_singleton_remove_branch_remote_eof_trigger.py`
  - inputs:
    - `/tmp/exception-failure-branch.json`
    - `/tmp/exception-peer-timeline.json`
  - result:
    - `remove_branch_established = true`
    - `remote_eof_singleton = true`
    - `result = singleton_promotion_member_is_sent_to_remove_branch_by_transport_handshake_remote_eof`
  - 의미:
    - singleton promotion member는
    - `transport/handshake` 응답 뒤 `remote_eof`를 받아 remove branch로 빠짐

- 2026-05-03 same-round remote_eof distribution:
  - checker:
    - `tools/check_same_round_remote_eof_distribution.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `1777819495994`
    - `1`
  - result:
    - `same_round_count = 7`
    - `remote_eof_count = 7`
    - `direct_full_connect_count = 1`
    - `result = all_same_round_members_get_remote_eof_so_exception_is_branch_specific_not_eof_specific`
  - 의미:
    - 같은 fan-out round의 모든 member가 `remote_eof`를 받음
    - 따라서 long-gap exception의 차이는 `EOF 발생 자체`가 아니라 `EOF를 받는 branch`에 있음

- 2026-05-03 singleton branch specificity:
  - checker:
    - `tools/check_singleton_branch_specificity.py`
  - inputs:
    - `/tmp/same-round-remote-eof.json`
    - `/tmp/exception-full-connect-path.json`
    - `/tmp/exception-failure-branch.json`
  - result:
    - `eof_is_round_wide = true`
    - `singleton_is_unique_full_connect_member = true`
    - `singleton_is_unique_remove_branch_member = true`
    - `result = singleton_member_is_branch_specific_full_connect_remove_member_while_remote_eof_is_round_wide`
  - 의미:
    - 같은 fan-out round에서 `remote_eof`는 공통 현상임
    - 차이는 `EOF 자체`가 아니라 singleton member만 `full-connect promotion/remove` branch 위에 있다는 점임

- 2026-05-03 why singleton member is branch candidate:
  - checker:
    - `tools/check_why_singleton_member_is_branch_candidate.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/exception-round-role.json`
  - result:
    - `source_has_probe_to_connecting_peer_path = true`
    - `source_has_connected_peer_request_peers_path = true`
    - `artifact_has_singleton_direct_full_connect_member = true`
    - `result = singleton_member_is_branch_candidate_because_only_it_is_on_probe_to_full_connect_path_while_others_are_request_peers_members`
  - 의미:
    - 같은 fan-out round의 singleton member만 `startProbe -> createConnectingPeer -> establishConnection -> connectToRemoteMasterNode` 경로 위에 있음
    - 나머지 round members는 이미 연결된 peer에 대한 `request_peers` members임

- 2026-05-03 singleton probe candidate dedup:
  - checker:
    - `tools/check_singleton_probe_candidate_dedup.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/pre-exception-sequence.json`
  - result:
    - `source_dedups_probe_candidates_by_address = true`
    - `request_peers_count = 3`
    - `tcp_handshake_count = 2`
    - `transport_handshake_followups = 1`
    - `result = same_round_multiple_probe_triggers_collapse_to_single_connecting_peer_candidate_via_peersByAddress_dedup`
  - 의미:
    - 같은 fan-out round 안에는 여러 probe trigger가 있음
    - 하지만 source의 `peersByAddress.computeIfAbsent(...)` 때문에 실제 connecting peer candidate는 하나로 수렴함

- 2026-05-03 single remote seed candidate in mixed probe:
  - checker:
    - `tools/check_single_remote_seed_candidate_in_mixed_probe.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `tools/probe_java_rust_mixed_membership.sh`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `source_skips_local_probe = true`
    - `runtime_uses_two_seed_hosts = true`
    - `runtime_has_single_remote_seed_identity = true`
    - `seed_transport_address = 127.0.0.1:48417`
    - `result = mixed_probe_has_two_seed_hosts_but_peerfinder_skips_local_one_so_probe_triggers_collapse_to_single_remote_seed_candidate`
  - 의미:
    - mixed probe는 seed host를 Java/Rust 2개로 주지만
    - `startProbe()`가 local address를 건너뛰므로 Rust 쪽 실제 remote seed candidate는 Java 1개로 collapse됨

- 2026-05-03 same-round request_peers burst means multiple address-keyed peers:
  - checker:
    - `tools/check_same_round_request_peers_implies_multiple_address_keyed_peers.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/exception-round-role.json`
  - result:
    - `source_uses_address_keyed_peers = true`
    - `source_wakeup_requests_peers_per_connected_peer = true`
    - `same_round_request_peers_count = 3`
    - `result = same_round_request_peers_burst_implies_multiple_address_keyed_connected_peer_entries_not_multiple_seed_candidates`
  - 의미:
    - same-round의 `request_peers` 3건은 remote seed candidate가 3개라는 뜻이 아님
    - source 기준으로는 address-keyed connected peer entry가 여러 개 있어서 wakeup 때 각각 `requestPeers()`를 보내는 상황에 더 가깝음

- 2026-05-03 multiple address-keyed alias peers:
  - checker:
    - `tools/check_multiple_address_keyed_alias_peers.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/exception-round-role.json`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
  - result:
    - `source_keys_peers_by_probe_address = true`
    - `source_does_not_rekey_to_canonical_remote_address = true`
    - `same_round_request_peers_count = 3`
    - `canonical_remote_transport_address = 127.0.0.1:48417`
    - `result = multiple_address_keyed_peer_entries_can_persist_as_aliases_of_single_canonical_remote_node`
  - 의미:
    - `PeerFinder`는 probe address를 key로 유지한 채 `discoveryNode=remoteNode`만 설정함
    - 그래서 single canonical remote node에 대해서도 alias address 기반 peer entries가 공존할 수 있음

- 2026-05-03 alias entries not from request_peers responses:
  - checker:
    - `tools/check_alias_entries_not_from_request_peers_response.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `1777819495994`
  - result:
    - `source_request_peers_response_can_only_start_probes_from_response_nodes = true`
    - `same_round_request_peers_count = 3`
    - `response_message_lengths = [29]`
    - `all_minimal_emptyish = true`
    - `result = same_round_alias_entries_are_not_explained_by_request_peers_responses_so_remaining_sources_are_cluster_state_or_configured_hosts`
  - 의미:
    - same-round `request_peers` 응답은 빈 응답에 가깝고
    - alias entry source를 설명하기에는 부족하므로 남는 후보는 `cluster state cluster-manager nodes`와 `configured hosts`임

- 2026-05-03 remaining alias entry source candidates:
  - checker:
    - `tools/check_cluster_state_vs_configured_hosts_candidates.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `tools/probe_java_rust_mixed_membership.sh`
  - result:
    - `source_has_cluster_state_cluster_manager_probe_source = true`
    - `source_has_configured_hosts_probe_source = true`
    - `runtime_sets_dual_seed_hosts = true`
    - `runtime_validated_mode_expands_initial_cluster_manager_nodes_to_java_and_rust = true`
    - `result = current_mixed_probe_runtime_exposes_both_cluster_state_cluster_manager_nodes_and_configured_hosts_as_remaining_alias_entry_sources`
  - 의미:
    - current mixed probe runtime은 alias entry source 후보로 `cluster state cluster-manager nodes`와 `configured hosts`를 둘 다 남김
    - 다음 단계는 실제 multiplicity를 어느 축이 만드는지 더 직접 분리하는 것임

- 2026-05-03 alias multiplicity requires cluster-state contribution:
  - checker:
    - `tools/check_multiplicity_requires_cluster_state_contribution.py`
  - inputs:
    - `/tmp/single-remote-seed-candidate.json`
    - `/tmp/multiple-address-keyed-peers.json`
    - `/tmp/source-candidates.json`
  - result:
    - `configured_hosts_side_collapses_to_one_remote_candidate = true`
    - `artifact_has_alias_multiplicity = true`
    - `source_exposes_both_candidate_axes = true`
    - `result = configured_hosts_alone_cannot_explain_alias_multiplicity_so_cluster_state_cluster_manager_nodes_must_contribute`
  - 의미:
    - configured hosts 축만으로는 alias multiplicity를 설명할 수 없음
    - actual multiplicity에는 `cluster state cluster-manager nodes` 축이 반드시 기여함

- 2026-05-03 configured host base one plus cluster-state additions:
  - checker:
    - `tools/check_configured_host_plus_cluster_state_additions.py`
  - inputs:
    - `/tmp/single-remote-seed-candidate.json`
    - `/tmp/multiple-address-keyed-peers.json`
    - `/tmp/cluster-state-contribution.json`
  - result:
    - `configured_hosts_base_one = true`
    - `same_round_request_peers_count = 3`
    - `cluster_state_must_contribute = true`
    - `cluster_state_additional_count_lower_bound = 2`
    - `result = alias_multiplicity_best_matches_configured_host_base_one_plus_cluster_state_additional_entries`
  - 의미:
    - actual multiplicity는 configured host 1개만으로 설명되지 않음
    - 현재 best fit은 `configured host base 1개 + cluster-state 추가 최소 2개` 조합임

- 2026-05-03 cluster-state aliases share one canonical Rust address:
  - checker:
    - `tools/check_cluster_state_aliases_share_canonical_rust_address.py`
  - inputs:
    - `/tmp/cluster-state-contribution.json`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/opensearch/stdout.log`
  - result:
    - `cluster_state_must_contribute = true`
    - `unique_canonical_rust_addresses = [127.0.0.1:38113]`
    - `unique_canonical_rust_address_count = 1`
    - `result = cluster_state_additional_aliases_do_not_appear_as_distinct_rust_transport_addresses_in_logs_and_instead_share_one_canonical_rust_address`
  - 의미:
    - cluster-state 추가분은 high-level log에서 distinct Rust transport address로 드러나지 않음
    - 보이는 canonical Rust address는 `127.0.0.1:38113` 하나뿐이며, 추가분은 hidden alias entry로 보는 편이 맞음

- 2026-05-03 hidden alias not persisted in Steelsearch state:
  - checker:
    - `tools/check_hidden_alias_not_persisted_in_steelsearch_state.py`
  - inputs:
    - `/tmp/canonical-rust-addresses.json`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/steelsearch/data/gateway-state.json`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/steelsearch/data/production-membership.json`
  - result:
    - `canonical_only_one_rust_address = true`
    - `gateway_rust_addresses = [127.0.0.1:38113]`
    - `membership_has_no_transport_addresses = true`
    - `result = hidden_alias_is_not_persisted_in_steelsearch_gateway_or_membership_state_and_remains_transient_peerfinder_side_keying`
  - 의미:
    - hidden alias는 Steelsearch canonical state에 저장되지 않음
    - current artifact 기준으로는 Java-side transient `PeerFinder` keying에만 남는 것으로 보는 편이 맞음

- 2026-05-03 raw probe address not directly exposed in current artifact:
  - checker:
    - `tools/check_raw_probe_address_not_directly_exposed.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/steelsearch/data/gateway-state.json`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/opensearch/stdout.log`
  - result:
    - `report_has_seed_identity_only = true`
    - `report_has_no_java_peerfinder_map = true`
    - `gateway_transport_addresses = [127.0.0.1:38113, 127.0.0.1:48417]`
    - `gateway_only_exposes_canonical_addresses = true`
    - `stdout_has_no_raw_peerfinder_probe_key_dump = true`
    - `result = current_artifact_does_not_directly_expose_java_peerfinder_raw_probe_addresses`
  - 의미:
    - current artifact만으로는 Java-side `PeerFinder` raw probe key를 직접 볼 수 없음
    - 다음 단계에서는 Java-side 계측/TRACE 경로를 추가로 찾아야 함

- 2026-05-03 PeerFinder TRACE logging route exists:
  - checker:
    - `tools/check_peerfinder_trace_logging_route.py`
  - inputs:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
    - `/tmp/java-rust-mixed-membership.X3Ig4M/opensearch/stdout.log`
  - result:
    - `source_has_trace_logs_for_raw_probe_flow = true`
    - `source_peer_to_string_includes_transport_address_and_discovery_node = true`
    - `current_stdout_lacks_peerfinder_trace = true`
    - `result = existing_peerfinder_trace_logging_route_can_expose_raw_probe_keys_but_is_not_enabled_in_current_artifact`
  - 의미:
    - 새 Java 코드 계측이 없어도 `PeerFinder` TRACE만 켜면 raw probe key를 볼 가능성이 높음
    - current artifact에서는 그 TRACE가 아직 비활성임

- 2026-05-04 PeerFinder TRACE enabled in actual mixed probe:
  - checker:
    - `tools/check_peerfinder_trace_enabled_actual_probe.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.8WbNRb/opensearch/stdout.log`
  - result:
    - `probing_resolved_count = 319`
    - `attempting_connection_count = 106`
    - `requesting_peers_count = 125`
    - `skipped_local_addresses = [127.0.0.1:57079]`
    - `remote_probe_addresses = [127.0.0.1:57743]`
    - `attempting_connection_addresses = [127.0.0.1:57743]`
    - `result = peerfinder_trace_is_enabled_in_actual_probe_and_exposes_raw_probe_addresses`
  - 의미:
    - runner pass-through는 실제로 동작함
    - current TRACE artifact에서 직접 보이는 raw probe address는 local skip `127.0.0.1:57079`와 remote `127.0.0.1:57743`임
    - 따라서 다음 단계는 이 actual TRACE와 earlier hidden-alias 가설을 대조하는 것임

- 2026-05-04 hidden-alias hypothesis status after TRACE:
  - checker:
    - `tools/check_hidden_alias_hypothesis_status_after_trace.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.X3Ig4M/report.json`
    - `/tmp/java-rust-mixed-membership.8WbNRb/report.json`
    - `/tmp/new-trace-enabled.json`
  - result:
    - `same_stage = true`
    - `current_trace_shows_only_single_remote_probe = true`
    - `old_artifact_only_implied_hidden_alias_indirectly = true`
    - `result = current_trace_does_not_directly_confirm_hidden_alias_so_previous_hidden_alias_claim_should_be_treated_as_indirect_inference`
  - 의미:
    - hidden alias는 current TRACE artifact에서 직접 확인되지 않음
    - 따라서 이전 hidden-alias 주장은 direct observation이 아니라 indirect inference로 취급해야 함

- 2026-05-04 direct multiplicity in TRACE-enabled artifact:
  - checker:
    - `tools/check_trace_artifact_direct_multiplicity.py`
  - inputs:
    - `/tmp/java-rust-mixed-membership.8WbNRb/opensearch/stdout.log`
  - result:
    - `attempting_connection_addresses = [127.0.0.1:57743]`
    - `requesting_peers_addresses = [127.0.0.1:57743]`
    - `resolved_probe_addresses = [127.0.0.1:57743]`
    - `result = trace_enabled_artifact_currently_reproduces_single_address_peer_activity_not_direct_alias_multiplicity`
  - 의미:
    - current TRACE-enabled artifact가 직접 재현하는 peer activity는 single-address임
    - 따라서 이전 transport-capture 기반 multiplicity 해석은 재검토가 필요함

- 2026-05-04 transport-capture multiplicity reinterpretation:
  - checker:
    - `tools/check_transport_capture_multiplicity_reinterpretation.py`
  - inputs:
    - `/tmp/old-round-role.json`
    - `/tmp/trace-direct-multiplicity.json`
  - result:
    - `old_request_peers_burst_present = true`
    - `trace_shows_single_requesting_peer_address = true`
    - `trace_shows_single_attempting_address = true`
    - `result = old_transport_capture_request_peers_burst_is_better_explained_as_repeated_one_shot_sockets_from_single_peer_than_as_multi_address_peer_multiplicity`
  - 의미:
    - old transport-capture의 `request_peers` burst는 여러 peer/address의 동시 활동보다
    - 단일 peer가 one-shot socket을 반복 개설하는 패턴으로 보는 편이 더 맞음

- 2026-05-04 multiplicity conclusion retirement:
  - checker:
    - `tools/check_multiplicity_conclusion_retirement.py`
  - inputs:
    - `/tmp/multiplicity-reinterpretation.json`
    - `/tmp/hidden-alias-status.json`
  - result:
    - `reinterpretation_established = true`
    - `hidden_alias_downgraded = true`
    - `result = previous_multi_address_hidden_alias_conclusions_should_be_retired_or_downgraded_in_favor_of_single_peer_repeated_one_shot_socket_explanation`
  - 의미:
    - 이전 `multi-address/hidden-alias` 계열 결론은 이제 direct evidence 기준선이 아님
    - 이후 분석은 `single peer repeated one-shot sockets` 설명을 기준으로 다시 세우는 편이 맞음

- 2026-05-04 blocker reframed as single-peer one-shot loop:
  - checker:
    - `tools/check_blocker_reframed_as_single_peer_one_shot_loop.py`
  - inputs:
    - `/tmp/trace-direct-multiplicity.json`
  - result:
    - `single_remote_peer = true`
    - `attempting_connection_addresses = [127.0.0.1:57743]`
    - `requesting_peers_addresses = [127.0.0.1:57743]`
    - `result = current_blocker_is_better_reframed_as_single_remote_peer_repeated_one_shot_connection_loop_than_as_multi_address_alias_multiplicity`
  - 의미:
    - current blocker를 설명하는 기준선은 더 이상 multi-address alias가 아님
    - single remote peer에 대한 repeated one-shot connection loop로 보는 편이 더 맞음

- 2026-05-04 single-peer loop settle loss point:
  - checker:
    - `tools/check_single_peer_loop_settle_loss_point.py`
  - inputs:
    - `/tmp/single-peer-loop.json`
    - `/tmp/java-rust-mixed-membership.8WbNRb/report.json`
  - result:
    - `single_remote_peer = true`
    - `direct_full_connect_count = 27`
    - `closes_before_post_request_count = 27`
    - `result = single_peer_one_shot_loop_loses_settle_at_direct_full_connect_transport_handshake_remote_eof_before_any_post_handshake_request`
  - 의미:
    - current loop는 direct full-connect `transport/handshake`까지는 감
    - 하지만 그 응답 뒤 post-handshake request 하나 보내기 전에 항상 `remote_eof`로 끊겨 settle을 잃음

- 2026-05-04: TRACE artifact에서 127.0.0.1:57743에 대해 `requesting peers`와 `connection failed`가 공존한다. direct full-connect remote_eof가 항상 Java `connectToRemoteMasterNode(...).onFailure`로 귀결되는지, 아니면 일부 probe/request_peers success 이후 새 Peer 객체가 다시 failure loop에 들어가는지 추가 분리가 필요하다.

- 2026-05-04: 127.0.0.1:57743에서 `discoveryNode={rust-replica-1} requesting peers` 상태와 `discoveryNode=null connection failed` 상태가 같은 로그에 공존한다. 다음은 어떤 close/unregister event가 connected peer를 지우고 fresh null-discovery Peer를 다시 만들게 하는지다.

- 2026-05-04: current TRACE/runtime에서는 connected `requesting peers` 뒤 `FollowersChecker disconnected/marking node as faulty` 후 fresh null-discovery `attempting connection` 재진입이 보인다. 하지만 정확히 어느 connection close callback이 `PeerFinder` 재생성을 유발하는지는 여전히 Java internals 추가 분리가 필요하다.

- 2026-05-04: callback boundary는 `connection close listener -> onNodeDisconnected -> FollowersChecker.handleDisconnectedNode/failNode("disconnected")`까지는 고정됐다. 다음 남은 질문은 이 뒤에 `PeerFinder`가 어떤 wakeup/reprobe 경로로 fresh null-discovery peer를 다시 만드는지다.

- 2026-05-04: current source/runtime 기준 fresh null-discovery 재진입은 direct FollowersChecker callback보다 PeerFinder scheduled handleWakeUp/findPeersInterval reprobe 쪽이 더 가깝다. 남은 질문은 왜 이 scheduled reprobe가 반복돼도 settled connectedNodes reuse로 회복되지 않는가다.

- 2026-05-04: scheduled PeerFinder reprobe는 회복 경로가 아니라 다시 같은 direct full-connect `transport/handshake -> remote_eof -> close-listener unregister` loop로 돌아간다. 남은 질문은 왜 이 direct full-connect handshake socket이 매번 그 지점에서 끊기는가다.

- 2026-05-04: current trace artifact에서 direct full-connect handshake socket은 local hold-open 뒤에도 `714ms~814ms` 안에 peer-side `remote_eof`로 끊기며 post-request까지 가지 못한다. 다음은 이 sub-second abort window가 Java 쪽 어떤 timeout/decision과 맞물리는지다.

- 2026-05-04: current direct full-connect abort window `714ms~814ms`는 `discovery.probe.handshake_timeout=1000ms` 축과 더 가깝고 `probe.connect_timeout=3000ms`, `follower_check.timeout=10000ms` 축과는 멀다. 다음은 이 1s-scale window 안에서 Java가 어떤 decision으로 peer-side abort를 내리는지다.

- 2026-05-04: HandshakingTransportAddressConnector TRACE에서는 `handshake successful` 뒤 `completed full connection`이 반복되고 `followup connection failed`는 0건이다. 따라서 `714ms~814ms` abort는 connector의 `connectToNode` 실패가 아니라 full connection completion 이후 채널 lifecycle에서 생긴다.

- 2026-05-04: current TRACE/report를 합치면 abort stage는 `connectToNode` completion 이후이면서 same socket의 첫 post-handshake reuse 이전이다. 다음은 왜 multi-channel/default profile 쪽 reuse 전에 채널 retention이 깨지는지다.

- 2026-05-04: current TRACE/report에서는 `completed full connection`이 있어도 `request_peers`, `follower_check`, `publish_state`가 모두 fresh first-frame sockets로만 보인다. 다음은 왜 retained default multi-channel reuse가 붙지 않고 매번 fresh socket만 생기는지다.

- 2026-05-04: source의 `requestPeers()`는 retained `getConnection(node)`를 전제하지만 current runtime에서는 `request_peers`, `follower_check`, `publish_state`가 전부 fresh first-frame socket이다. 즉 retained channel은 request 시점 이전에 이미 사라진다. 다음은 connect completion 직후 어떤 channel class/close event가 먼저 무너지는지다.

- 2026-05-04: current artifact가 직접 말할 수 있는 최선은 `connectToNode` establishment handshake socket이 default multi-channel class별 retained reuse가 관측되기 전에 먼저 `remote_eof`로 무너진다는 점이다. class별 최초 파손 순서를 더 보려면 Java transport/channel instrumentation이 추가로 필요하다.

- 2026-05-04: existing transport tracer는 action/node 수준까지만 보이고 channel class 선택 자체는 드러내지 않는다. class별 최초 파손 순서를 보려면 `ConnectionProfile.ConnectionTypeHandle#getChannel()`와 `ClusterConnectionManager` connected close-listener 경계에 Java-side instrumentation을 추가해야 한다.

- 2026-05-04: runner/actual probe 경로는 `ClusterConnectionManager` unregister trace와 connector full-connection trace는 노출하지만, current probe에서는 `ConnectionProfile#getChannel()` TRACE가 아직 0건이다. 다음은 왜 이 trace가 current path에서 보이지 않는지 분리해야 한다.

- 2026-05-04: correction: `selected channel index` TRACE는 outer `ConnectionProfile.class`가 아니라 inner `ConnectionProfile$ConnectionTypeHandle.class`에 들어간다. build class와 distribution jar 둘 다 이 inner class 문자열을 이미 포함한다. 따라서 `ConnectionProfile#getChannel()` TRACE 0건의 직접 원인은 build/runtime artifact mismatch가 아니라 current mixed runtime이 Java-side `NodeChannels#getChannel()` send path에 실제로 도달하지 않거나, 그에 준하는 runtime reachability 문제일 가능성이 더 높다.

- 2026-05-04: `OPENSEARCH_FORCE_GRADLE_RUN=1` runner/probe 경로는 구현했지만 current mixed probe에서는 `opensearch_startup_timeout`으로 끝났다. source-backed runtime 비교는 더 긴 startup budget 또는 별도 Java-only validation 경로가 필요할 수 있다.

- 2026-05-04: source 상으로는 `PeerFinder.requestPeers()` -> `TransportService.getConnection(node)` -> `Transport.Connection.sendRequest()` -> local-cluster `TcpTransport.NodeChannels.channel(options.type())` -> `ConnectionTypeHandle#getChannel()` 경로가 맞다. `ProxyConnection`은 `RemoteConnectionManager` 쪽 remote-cluster 전용이다. 그런데 current mixed runtime 로그에서는 `selected channel index` TRACE가 0건이고 report에는 inbound fresh first-frame sockets만 반복된다. 다음은 어떤 runtime branch가 Java-side retained send path 관측을 가리거나 우회하는지다.

- 2026-05-04: latest synthesis는 “다른 connection class를 쓴다”보다 `ClusterConnectionManager` close-listener unregister -> reconnect branch 쪽이 더 가깝다. full connection completion 뒤 unregister가 반복되고, Rust 쪽에는 `request_peers`/`follower_check`/`publish_state`가 모두 fresh first-frame-only로 남는다. 다음은 왜 same socket reuse가 그 unregister 이전에 한 번도 붙지 못하는지다.

- 2026-05-04: `PeerFinder` source상 `connectToRemoteMasterNode(...).onResponse`는 `discoveryNode.set(remoteNode)` 직후 바로 `requestPeers()`를 호출한다. 그런데 runtime에서는 `request_peers`가 여전히 fresh first-frame-only socket이고, direct full-connect `transport/handshake` socket은 post-frame 없이 handshake-only로 남다가 unregister된다. 다음은 왜 첫 eligible `requestPeers()`조차 same socket reuse가 아니라 separate fresh socket branch로 가는지다.

- 2026-05-04: correction: source상 probe `transport/handshake` connection은 `handshake successful` 직후 `IOUtils.closeWhileHandlingException(connection)`으로 명시적으로 닫힌 뒤 `transportService.connectToNode(remoteNode)`가 full connection을 연다. 따라서 immediate `requestPeers()`가 same probe socket reuse로 가지 않는 것 자체는 expected이다. 남은 질문은 왜 그 full multi-channel connection 쪽 retained reuse도 실제로 붙지 못하고 fresh first-frame sockets만 남는지다.

- 2026-05-04: latest artifact에서는 full connection 이후의 `request_peers`/`follower_check`/`publish_state` sockets가 전부 response 직후 `remote_eof`, follow-up 없음 패턴이다. 즉 문제는 probe socket reuse가 아니라 full connection action channels 자체가 one-shot으로 무너진다는 점이다. 다음은 왜 이 action channels가 첫 response 직후 바로 끊기는지다.

- 2026-05-04: Rust transport handler는 `request_peers`/`follower_check`/`publish_state` 응답 뒤 각각 15~20초 hold-open을 시도하고, `hold_transport_channel_open(...)`은 EOF/idle/ping/follow-up을 기다린다. current artifact는 이 action channels가 모두 `remote_eof`로 끝난다. 따라서 닫는 쪽은 Rust가 아니라 Java peer다. 다음은 Java peer가 왜 첫 response 직후 이 channels를 닫는지다.

- 2026-05-04: `TcpTransport` source에서는 full connection의 handshake channel이 `channels.get(0)`이고, 어떤 channel이든 close되면 `ch.addCloseListener(... nodeChannels::close)`를 통해 whole `NodeChannels` close로 fan-out된다. current artifact에는 direct full-connect `transport/handshake` channel의 `remote_eof`와 action channels의 `remote_eof`가 함께 보인다. 다음은 이 handshake channel close fan-out이 whole connection teardown의 직접 원인인지 더 분리하는 것이다.

- 2026-05-04: current artifact에서는 direct full-connect `transport/handshake` socket의 `remote_eof`와 sibling `request_peers`/`follower_check` sockets의 `remote_eof`가 같은 burst 안에서 거의 같은 시각에 반복 공존한다. 이는 whole connection teardown fan-out 설명을 더 강하게 지지한다. 다음 남은 질문은 왜 handshake channel이 먼저 `remote_eof`를 받느냐이다.

- 2026-05-04: Java `TransportHandshaker`의 정상 success path는 `listener.onResponse(version)`만 호출하고 channel을 닫지 않으며, handshake response decode 시 `removeHandlerForHandshake(requestId)`로 pending handler도 정상 제거된다. 따라서 direct full-connect handshake channel의 `remote_eof`는 local success-cleanup보다는 peer-side close로 보는 편이 맞다. 다음은 그 peer-side 원인이다.

- 2026-05-04: burst timing을 보면 handshake `remote_eof`와 sibling `request_peers`/`follower_check` `remote_eof`는 거의 같은 시각에 떨어진다. current artifact만으로는 handshake channel이 단독으로 먼저 죽어서 나머지를 끌고 간다고 단정하기보다, peer-side whole-burst close decision으로 읽는 편이 더 맞다. 다음은 그 whole-burst close decision 자체다.

- 2026-05-04: current source/runtime에서는 `ClusterConnectionManager` unregister 뒤 `FollowersChecker disconnected/marking node as faulty`, 그리고 reconnect + `completed full connection`이 반복된다. 따라서 current peer-side whole-burst close는 handshake-channel 특수 원인보다 Java node-level disconnect/fault/reconnect policy 쪽이 더 가깝다. 다음 남은 질문은 이 policy 안에서 최초 close decision을 실제로 누가 내리느냐다.

- 2026-05-04: `FollowersChecker` fault path는 `Coordinator.removeNode`에 연결되지만, runtime에서는 `marking node as faulty` 직후 `PeerFinder`가 같은 rust 노드를 cluster state에서 다시 probe한다. 따라서 Java node-level disconnect/fault/reconnect policy는 최초 close decider가 아니라 이미 닫힌 connection에 반응하는 reactive path로 보인다. 다음 남은 질문은 최초 peer-side whole-burst close decision을 실제로 누가 내리느냐다.

- 2026-05-04: current source/runtime에서는 최초 whole-burst close decision이 `FollowersChecker`/`Coordinator` policy가 아니라 그보다 앞선 upstream connection close signal로 `ClusterConnectionManager`에 먼저 도달한다. 따라서 다음 남은 질문은 이 close signal의 lower transport source가 무엇이냐이다.

- 2026-05-04: current source/runtime에서는 최초 upstream close signal의 lower transport source가 `TcpTransport.NodeChannels` close fan-out 쪽으로 좁혀졌다. 다음 남은 질문은 어떤 individual TcpChannel이 이 fan-out을 처음 트리거하느냐다.

- 2026-05-04: current artifact에서는 대부분의 burst가 near-simultaneous `remote_eof`로 묶여 있어서 어떤 individual TcpChannel이 `NodeChannels` fan-out을 처음 트리거했는지 직접 식별하지 못한다. 다음 남은 질문은 per-channel close ordering을 보이게 하는 Java transport instrumentation을 어디에 둘 것이냐다.

- 2026-05-04: `TcpTransport` per-channel close ordering TRACE와 mixed runner/probe log-level pass-through는 구현됐고 compiled `TcpTransport$ChannelsConnectedListener.class`에도 반영됐다. 다음 남은 질문은 actual probe에서 이 TRACE가 실제로 찍히는지다.

- 2026-05-04: actual probe에서 `TcpTransport` per-channel close ordering TRACE는 실제로 찍혔다. 분포상 `channelIndex 0`가 dominant unique first close index지만 same-timestamp ambiguous connection이 41건 남는다. 다음 남은 질문은 이 ambiguous cases를 더 쪼갤 finer ordering instrumentation/clock source가 무엇이냐이다.

- 2026-05-04: finer ordering instrumentation(`closeOrder`/`closeNanoTime`)은 source와 compiled `TcpTransport$ChannelsConnectedListener.class`에는 들어갔지만 current distro actual probe runtime에는 아직 없다. distro jar의 same class에는 이 문자열이 없고 actual probe stdout도 old trace만 찍는다. 다음 남은 질문은 rebuilt distribution 또는 다른 runtime 경로로 이 instrumentation을 실제 probe에 싣는 방법이다.

- 2026-05-04: rebuilt-runtime overlay actual probe에서 `closeOrder`/`closeNanoTime` TRACE는 실제로 찍혔고 same-ms ambiguity는 제거됐다. 하지만 first-close 분포는 `channelIndex 0` dominant일 뿐 universal은 아니다. 다음 남은 질문은 `1/2/6/...` index가 source의 어떤 profile channel class에 대응하느냐다.

- 2026-05-04: overlay actual probe의 `closeOrder` first-close index 분포를 source default profile range에 붙이면 `BULK=112`, `RECOVERY=21`, `REG=7`, `PING=0`, `STATE=0`으로 매핑된다. 따라서 다음 남은 질문은 왜 first-close가 `BULK/RECOVERY`에 몰리고 `PING/STATE`는 비는지다.
- 2026-05-04: overlay actual probe에서 first-close class 분포는 action 사용량과 맞지 않는다. `follower_check(PING)=27`, `publish_state(STATE)=2`, `request_peers(REG)=48`가 실제로 존재하는데도 first-close는 `PING=0`, `STATE=0`, `REG=7`, `BULK=112`, `RECOVERY=21`이다. 다음 남은 질문은 왜 lower transport close origin이 `BULK/RECOVERY` 쪽에 치우치는지, 그리고 그것이 `bulk/recovery` 업무 자체인지 아니면 idle/default channel ordering artifact인지다.
- 2026-05-04: actual report action hints에는 `request_peers`, `follower_check`, `publish_state`, `start_join`, `request_pre_vote`, `tcp/handshake`, `transport/handshake`만 있고 `bulk`/`recovery` 상위 action은 없다. 그런데 first-close class는 `BULK=112`, `RECOVERY=21`로 몰린다. 따라서 다음 남은 질문은 이 편향이 실제 bulk/recovery 업무가 아니라 default profile의 idle/lower-transport close ordering artifact인지다.
- 2026-05-04: `bulk/recovery` 상위 workload 부재뿐 아니라 first-close low indices `0/1/2=112`, `5/6=21`, later `REG=7` 분포도 class semantics보다 low-index bias 쪽과 더 잘 맞는다. 다음 남은 질문은 이 low-index bias가 actual first-origin 편향인지, 아니면 `CloseableChannel.closeChannels(channels)` fan-out / logging ordering artifact인지다.
- 2026-05-04: finer `closeOrder` trace에서 nonzero first index가 `70/140`이고 `1/2/5/6/7/9/10/12`까지 직접 보인다. 따라서 current low-index bias는 pure `closeChannels(list-order)` logging artifact만으로는 설명되지 않는다. 다음 남은 질문은 왜 actual first-origin 자체가 low idle indices 쪽에 더 자주 붙는지다.
- 2026-05-04: source상 full connection channels는 index 순서대로 열리고 default profile도 `BULK -> PING -> STATE -> RECOVERY -> REG` 순으로 배치된다. current low-index first-origin bias는 active later action channels보다 earlier-opened idle `BULK/RECOVERY` siblings 쪽과 더 잘 맞는다. 다음 남은 질문은 왜 peer-side close가 바로 이 older idle siblings를 먼저 고르는지다.
- 2026-05-04: current artifact에서는 `bulk/recovery` 상위 action이 없고 later channels에는 `request_peers`, `follower_check`, `publish_state`, `start_join`, `request_pre_vote`, handshake traffic가 있다. 따라서 peer-side first close는 active later channels보다 traffic-free older `BULK/RECOVERY` siblings를 먼저 고르는 것으로 보인다. 다음 남은 질문은 어떤 lower transport policy가 이 traffic-free siblings를 close origin으로 선택하는지다.
- 2026-05-04: OpenSearch transport source에서는 channel `type`가 send selection에만 쓰이고 keepalive/close path는 모든 channels를 균일하게 다룬다. 따라서 `BULK/RECOVERY` siblings를 close origin으로 고르는 type-aware policy는 이 레이어에 없다. 다음 남은 질문은 Java source 아래 Netty/socket layer에서 왜 traffic-free siblings가 first close origin으로 선택되는지다.
- 2026-05-04: lower-layer close cause를 보기 위해 `Netty4MessageChannelHandler.exceptionCaught/channelInactive -> Netty4TcpChannel.closeFuture` close-hint TRACE 경로를 source와 compiled class에 추가했다. 다음 남은 질문은 이 `transport-netty4` class overlay를 actual distro probe runtime에 어떻게 싣고, close hint가 실제로 찍히는지다.
- 2026-05-04: `transport-netty4` overlay actual probe에서는 `netty4 tcp channel close completed ... with hint [...]` TRACE가 1101건 찍혔지만 값이 전부 `unknown`이다. 즉 `Netty4TcpChannel.closeFuture` TRACE는 runtime에 실렸지만 `exceptionCaught/channelInactive -> recordCloseHint(...)` propagation은 current actual path에서 아직 잡히지 않는다. 다음 남은 질문은 handler overlay 미적용인지, 아니면 closeFuture가 hint write보다 먼저 완료되는 ordering 문제인지다.
- 2026-05-04: `transport-netty4` overlay actual probe에서 `Netty4MessageChannelHandler.channelInactive` TRACE는 `1023건` 보이는데 `Netty4TcpChannel` close hint 값은 여전히 전부 `unknown`이다. 따라서 문제는 handler overlay 미적용이 아니라 `closeFuture` completion이 `recordCloseHint(...)`보다 먼저 관측되는 ordering race 쪽으로 좁혀진다. 다음 남은 질문은 hint를 더 이른 Netty hook/attribute에서 기록하도록 바꿔 race를 없애는 방법이다.
- 2026-05-04: `Netty4Transport$Netty4EarlyCloseHintHandler`를 dispatcher보다 앞단에 넣어도 actual fixed overlay probe에서는 `channelInactive` TRACE가 `1065건` 보이는데 close hint는 여전히 전부 `unknown`이다. 따라서 `channelInactive` 자체가 이미 `closeFuture`보다 늦다. 다음 남은 질문은 `channelInactive`보다 더 이른 Netty close hook 또는 close promise interception이 무엇인지다.
- 2026-05-04: `ClientChannelInitializer`에 `closeFutureIntercepted` listener를 추가해도 actual fixed overlay probe에서는 close hint가 여전히 전부 `unknown`이다. `channelInactive`는 `1067건` 보인다. 따라서 다음 남은 질문은 Netty hook 종류보다 `Netty4TcpChannel` close TRACE listener registration order 자체인지, 즉 constructor에서 붙는 listener를 더 늦게 등록해야 하는지다.

- 2026-05-04: `Netty4TcpChannel.installCloseTraceListener()`로 close TRACE listener를 constructor 밖으로 옮긴 late-listener 변경은 source와 compiled class에는 들어갔지만, current actual overlay probe artifact `/tmp/java-rust-mixed-membership.5KzGBt`는 `failure_stage = opensearch_startup_timeout`이고 `opensearch/stdout.log`가 비어 있다. 다음 남은 질문은 late-listener overlay 조합이 실제 distro startup regression을 일으킨 것인지, 아니면 runner/probe output corruption과 별개로 다른 runtime reachability 문제가 섞인 것인지다.

- 2026-05-04: late-listener overlay는 자체 startup regression으로 고정되지 않는다. direct runner `/tmp/opensearch-late-listener-direct.4023`에서는 OpenSearch가 정상 기동됐고, clean mixed rerun artifact `/tmp/java-rust-mixed-membership.JLetKF`도 `membership_timeout/standalone_only_bootstrap`까지 진행됐다. 게다가 close hint는 더 이상 all-unknown이 아니고 `closeFutureIntercepted=3`, `exceptionCaught=1`, `unknown=1113`으로 나뉜다. 다음 남은 질문은 이 non-unknown close hint들이 어떤 channel/action burst와 연결되는지다.

- 2026-05-04: clean mixed rerun `/tmp/java-rust-mixed-membership.JLetKF`에서 non-unknown close hint 4건은 `pre_local_bind_or_pre_first_frame_close` 1건, `internal:tcp/handshake` 매치 1건, `publication_failure_burst` 1건, `connection_reset_exception` 1건으로만 분류된다. 즉 non-unknown hint는 steady-state `request_peers/follower_check/publish_state`가 아니라 sparse failure burst에 붙는다. 다음 남은 질문은 왜 majority `unknown=1113`는 같은 방식으로 분류되지 못하는지다.

- 2026-05-04: clean mixed rerun의 `unknown=1113` majority는 미분류가 아니다. `35`건은 `local=null` pre-bind close이고, `1078`건은 close TRACE 뒤 `100` lines 안에 same localAddress `channelInactive`가 따라오는 post-bind late-handler race다. unexplained는 `0`이다. 다음 남은 질문은 `35`건 null-local pre-bind close가 어떤 outbound attempt phase인지다.

- 2026-05-04: clean mixed rerun의 `35`건 null-local pre-bind unknown close는 `127.0.0.1:40357` 단일 target에 거의 전부 몰리고, inter-close delta `34`개 중 `33`개가 `998ms~1002ms`이다. 따라서 이들은 repeated outbound attempt가 near-1s probe cadence로 돌다가 local bind/first-frame 이전에 닫히는 쪽으로 좁혀진다. 다음 남은 질문은 이 시도가 정확히 `HandshakingTransportAddressConnector` connect phase인지다.

- 2026-05-04: connector TRACE actual probe `/tmp/java-rust-mixed-membership.dIfIyb`에서 null-local pre-bind unknown close `34건`은 모두 `connectToRemoteMasterNode[127.0.0.1:34965] opening probe connection` 반복 구간에 들어간다. first `opened probe connection` 이전 집계도 `null_local=34`, `opening_probe=35`로 거의 1:1이다. 따라서 이 null-local closes는 `HandshakingTransportAddressConnector` opening-probe pre-open phase로 고정된다. 다음 남은 질문은 왜 opening probe `35`회 중 첫 successful `opened probe connection`이 그 시점에야 나오는지다.

- 2026-05-04: connector TRACE actual probe `/tmp/java-rust-mixed-membership.dIfIyb`에서 first successful `opened probe connection`은 `1777862953696ms`이고, Rust side first inbound capture는 `1777862953692ms`의 `internal:tcp/handshake`다. delta가 `4ms`뿐이므로, 그 전 opening probe 반복은 Java connector 이상보다 remote transport acceptance 이전 시도에 가깝다. 다음 남은 질문은 왜 Rust side transport acceptance가 바로 그 시점에야 열리는지다.

- 2026-05-04: current transport acceptance delay는 Rust 내부 late gate보다 probe start order / process start timing 쪽이 더 가깝다. `probe_java_rust_mixed_membership.sh`는 OpenSearch HTTP ready와 seed identity 수집 후에야 Steelsearch를 `cargo run`하고, Rust `main()`은 process가 뜨자마자 transport listener를 bind+serve한다. first `opened probe connection`과 first Rust inbound `internal:tcp/handshake` capture delta도 `4ms`다. 다음 남은 질문은 이 process start timing 안에서 `cargo run`/build가 실제로 얼마를 차지하느냐다.

- 2026-05-04: timing-instrumented probe `/tmp/java-rust-mixed-membership.VmODlD`에서 Steelsearch `cargo run` launch -> Rust transport bind는 `3000ms`, bind -> first inbound capture는 `703ms`, launch -> first inbound capture는 `3703ms`다. 따라서 current acceptance delay의 majority는 Rust process bind 이전 구간이다. 다음 남은 질문은 이 `3000ms` 안에서 cargo build와 process startup이 각각 얼마나 차지하느냐다.

- 2026-05-04: split-build timing probe `/tmp/java-rust-mixed-membership.rhyqnc`에서는 `cargo build = 83ms`, `binary exec -> bind = 5ms`, `bind -> first capture = 51ms`다. 따라서 earlier `~3000ms` bind-before gap의 majority는 Rust code startup이 아니라 plain `cargo run` wrapper 쪽이다. 다음 남은 질문은 왜 plain `cargo run`이 split build+exec보다 약 `3s` 느린지다.

- 2026-05-04: plain-path artifact `/tmp/java-rust-mixed-membership.VmODlD`와 split-path artifact `/tmp/java-rust-mixed-membership.rhyqnc` 비교 결과 `plain launch->bind = 3000ms`, `split build + exec->bind = 88ms`, 차액은 `2912ms`다. 따라서 majority delay는 actual build/runtime이 아니라 plain `cargo run` wrapper remainder다. 다음 남은 질문은 이 `2912ms`가 Cargo의 어떤 subphase인지다.

- 2026-05-04: warm plain-path rerun `/tmp/java-rust-mixed-membership.abfEHa`에서는 `launch->bind = 74ms`이다. 따라서 earlier `3000ms`를 stable `cargo run` wrapper overhead로 보는 것은 맞지 않고, cold incremental rebuild artifact로 내려야 한다. cold vs warm 차이는 `2926ms`다. 다음 남은 질문은 어떤 Rust source edit set이 이 cold rebuild cost를 유발했는지다.

- 2026-05-04: touch-based rebuild check에서 warm `cargo build = 70ms`, `crates/os-node/src/main.rs` touch 뒤 `1323ms`, `tools/run-steelsearch-dev.sh` touch 뒤 `68ms`다. 따라서 current cold incremental rebuild cost는 shell runner edit가 아니라 Rust source edit set, 최소한 `main.rs` 수준 변경에 의해 유발된다. 다음 남은 질문은 이 rebuild가 `os-node` 단일 crate recompilation인지 더 넓은 crate graph 전파인지다.

- 2026-05-04: `main.rs` touch 뒤 `cargo build -vv`에서 `dirty_crates = [os-node]`, `compiling_crates = [os-node]`만 보이고 다른 crate들은 fresh다. 따라서 current incremental rebuild scope는 wider crate graph 전파가 아니라 `os-node` 단일 crate recompilation이다. 다음 남은 질문은 `os-node` crate 내부에서 어떤 source file군이 비용을 가장 크게 만드는지다.

- 2026-05-04: `os-node` 내부 touch-based cost 비교에서 `main.rs = 1326ms`, `standalone_runtime.rs = 3654ms`, `lib.rs = 4281ms`다. 따라서 binary entrypoint edit보다 library path edit가 훨씬 비싸다. 다음 남은 질문은 왜 `lib.rs`/`standalone_runtime.rs` 경로가 `main.rs`보다 더 비싼지, 즉 binary-only recompilation과 library-path recompilation 차이가 무엇인지다.

- 2026-05-04: `cargo build -vv` compile unit 비교에서 `main.rs` touch는 `steelsearch` binary만 다시 컴파일하고, `lib.rs`/`standalone_runtime.rs` touch는 `os_node` library와 `steelsearch` binary를 둘 다 다시 컴파일한다. 따라서 library path edit의 고비용은 dual-target recompilation으로 설명된다. 다음 남은 질문은 `os_node` library compile과 `steelsearch` binary compile이 각각 시간에 얼마나 기여하는지다.

- 2026-05-04: `lib.rs` touch 뒤 분리 계측에서 `os_node` library compile = `2433ms`, 그 뒤 `steelsearch` binary compile = `1338ms`, 합계 `3771ms`다. 따라서 dual-target recompilation 중 더 큰 덩어리는 `os_node` library 쪽이다. 다음 남은 질문은 왜 `os_node` library compile이 binary compile보다 더 비싼지다.

- 2026-05-04: broad export surface checker 기준으로 `crates/os-node/src/lib.rs`는 `pub mod` 33개와 `pub use standalone_runtime::*` re-export를 가진다. measured rebuild도 `main.rs = 1308ms`, `lib.rs = 3607ms`, `standalone_runtime.rs = 3637ms`였고, compile units는 `main.rs -> [steelsearch]`, `lib.rs/standalone_runtime.rs -> [os_node, steelsearch]`였다. 또한 `lib.rs` touch 뒤 분리 계측은 `os_node` library compile = `2397ms`, `steelsearch` binary compile = `1313ms`였다. 따라서 현재 설명은 broad library export surface invalidation + dual-target recompilation이다. 다음 남은 질문은 `lib.rs`가 `standalone_runtime.rs`보다 추가로 비싸게 나오는 부분이 re-export/metadata invalidation 때문인지 더 분리하는 것이다.

- 2026-05-04: repeated timing 4회씩 재측정에서는 `lib.rs` samples=`[3609,3628,3631,3612]`, median=`3620ms`이고 `standalone_runtime.rs` samples=`[3631,3609,3677,3599]`, median=`3620ms`였다. range도 겹치고 median diff도 `0ms`다. 따라서 earlier single-run `lib.rs > standalone_runtime.rs` 차이는 stable하지 않으며, `re-export/metadata invalidation`을 file-level delta만으로 강하게 주장하면 안 된다. 다음 남은 질문은 file blame보다 rustc `--timings` 또는 self-profile에서 `os_node` library compile의 실제 phase hotspot이 무엇인지다.

- 2026-05-04: `cargo build --timings` actual run에서는 `os_node` library unit `duration=2360ms`, `rmeta_time=1950ms`, share=`82.6%`였고, 뒤따르는 `steelsearch` binary unit은 `1250ms`였다. 즉 current hotspot은 downstream binary가 아니라 library unit 자체이며, 그 안에서도 `rmeta/metadata` 비중이 지배적이다. 다음 남은 질문은 rustc self-profile 또는 더 세밀한 phase 출력에서 이 `rmeta` 시간 안의 세부 hotspot이 무엇인지다.

- 2026-05-04: nightly `cargo +nightly rustc --lib -- -Z time-passes` 재측정에서는 `os_node` library full compile top phases가 `codegen_crate=3.566s`, `LLVM_passes=3.149s`, `codegen_to_LLVM_IR=2.462s`였고 `generate_crate_metadata=0.120s`는 훨씬 작았다. 즉 nightly full compile phase view에서는 metadata 단독보다 codegen/LLVM이 더 크다. 다음 남은 질문은 왜 stable incremental `cargo --timings`는 `rmeta_time` 우세로 보이는데 nightly full-compile `time-passes`는 codegen/LLVM 우세로 보이는지, 즉 build mode/measurement semantics 차이를 더 분리하는 것이다.

- 2026-05-04: same nightly toolchain 비교에서 `cargo +nightly build --timings` incremental lib unit은 `duration=1.33s`, `frontend=0.93s`, `codegen=0.40s`, 뒤 binary는 `1.02s`였다. 반면 `cargo +nightly rustc --lib -- -Z time-passes` full library compile은 `codegen_crate=3.764s`, `LLVM_passes=3.296s`, `codegen_to_LLVM_IR=2.760s`, `generate_crate_metadata=0.129s`였다. 따라서 두 관측의 차이는 toolchain 자체가 아니라 measurement semantics와 build target 차이, 즉 incremental lib unit frontend timing vs full library compile phase timing으로 읽는 편이 맞다. 다음 남은 질문은 이 incremental frontend `0.93s` 안에서 실제 비용이 큰 query/phase가 무엇인지다.

- 2026-05-04: nightly `cargo +nightly rustc --lib -- -Z self-profile=/tmp/osnode-selfprofile`로 raw self-profile capture는 실제로 가능했고 `/tmp/osnode-selfprofile/os_node-1345318.mm_profdata`가 생성됐다. 하지만 current environment에는 `summarize`/`crox`가 PATH에 없고, `rustup component add rustc-tools --toolchain nightly`도 `aarch64` nightly에선 불가능했다. 또한 `cargo install measureme`는 library crate라 binary를 주지 않는다. 따라서 지금 남은 blocker는 raw capture가 아니라 compatible measureme summary tool 부재이며, 다음 남은 질문은 이 tool 경로를 어떻게 확보해 incremental frontend `0.93s`의 query-level hotspot을 실제로 뽑을지다.

- 2026-05-04: measureme GitHub 경로로 `cargo +nightly install --git https://github.com/rust-lang/measureme summarize` 설치가 실제로 성공했고, `summarize summarize /tmp/osnode-selfprofile/os_node-1345318.mm_profdata`로 query-level summary를 뽑았다. backend 항목을 제외한 top frontend-like hotspot은 `expand_crate=269.32ms`, `hir_crate=145.96ms`, `fn_abi_of_instance_no_deduced_attrs=128.92ms`, `compute_debuginfo_type_name=110.76ms`, `incr_comp_encode_dep_graph=77.58ms`, `expand_proc_macro=76.55ms`, `late_resolve_crate=75.45ms`였다. 다음 남은 질문은 이 hotspot들이 `lib.rs` broad module surface와 macro expansion fanout에 어떻게 연결되는지다.

- 2026-05-04: source fanout checker 기준으로 `crates/os-node/src/lib.rs`는 `pub mod 33개`를 re-export root에서 끌어오고, crate 전체는 `35`개 `.rs` 파일을 가진다. 또한 crate 전체 `#[derive(...)]`는 `101`개, 추가 proc-macro attr는 `18`개였고, `standalone_runtime.rs`는 혼자 `28775` lines다. 이를 self-profile top frontend-like hotspot `expand_crate/hir_crate/expand_proc_macro/late_resolve_crate`와 합치면 current frontend cost는 crate-root module fanout + proc-macro expansion pressure와 정렬된다고 보는 편이 맞다. 다음 남은 질문은 이 비용 중 `standalone_runtime.rs` giant body의 기여와 crate-wide fanout의 기여를 어떻게 더 분리하느냐다.

- 2026-05-04: giant body vs fanout 비교에서 `standalone_runtime.rs` touch와 51-line leaf `write_path_invariants.rs` touch는 둘 다 같은 compile units `[os_node, steelsearch]`를 다시 컴파일했고, rebuild time도 `3578ms` vs `3686ms`로 사실상 비슷했다. 따라서 current rebuild cost는 `standalone_runtime.rs` giant body 단독 우세보다는 shared crate-wide fanout이 더 가깝거나, 최소한 giant-body 우세 주장을 지지하지 않는다. 다음 남은 질문은 tiny leaf에서도 그대로 남는 이 shared fanout cost의 직접 source가 crate-root expansion인지 derive/proc-macro 재실행인지다.

- 2026-05-04: 51-line `write_path_invariants.rs`는 local `#[derive]`도 proc-macro attr도 `0`개다. 그런데 이 tiny leaf를 touch한 뒤 self-profile top frontend-like hotspot은 여전히 `expand_crate=278.99ms`, `hir_crate=150.18ms`, `expand_proc_macro=77.86ms`, `late_resolve_crate=76.86ms`로 유지된다. 따라서 shared fanout cost의 직접 source는 touched leaf body 자체가 아니라 crate-root expansion + crate-wide proc-macro rerun으로 보는 편이 맞다. 다음 남은 질문은 이 crate-wide proc-macro rerun 중 실제로 가장 큰 macro family가 무엇인지다.

- 2026-05-04: derive/attr family 계수에서 `Clone=100`, `Debug=98`, `Eq=88`, `PartialEq=88`는 높지만 built-in derive다. external proc-macro-like family는 사실상 `serde`가 지배적이고, `Serialize=43`, `Deserialize=43`, `serde::Deserialize=2`, `#[serde(...)] attr=18`로 합계 `106` site였다. 따라서 crate-wide proc-macro rerun의 최대 family는 `serde` 쪽으로 좁혀진다. 다음 남은 질문은 이 `serde` site가 어떤 module cluster에 몰려 있는지다.

- 2026-05-04: `serde`-like site per-file 분포를 보면 `standalone_runtime.rs=106`, `main.rs=2`뿐이라 총 `108` 중 `98.1%`가 `standalone_runtime.rs`에 몰린다. 따라서 crate-wide proc-macro rerun의 핵심 cluster는 사실상 `standalone_runtime.rs`다. 다음 남은 질문은 tiny leaf rebuild에서도 `lib.rs -> standalone_runtime` 경로가 왜 이 `serde` cluster 전체를 다시 끌어오는지다.

- 2026-05-04: aggregator checker 기준 `lib.rs`는 `pub mod standalone_runtime;`와 `pub use standalone_runtime::*;`를 둘 다 가지고 있고, tiny leaf rebuild에서도 `os_node` library target 재빌드와 `expand_crate/expand_proc_macro` hotspot이 유지된다. 동시에 `serde` cluster의 `98.1%`는 `standalone_runtime.rs`에 있다. 따라서 tiny leaf rebuild가 `standalone_runtime` cluster를 다시 끄는 직접 경로는 crate root include + reexport라고 보는 편이 맞다. 다음 남은 질문은 이 `pub use standalone_runtime::*` reexport가 실제로 필요한 public surface인지다.

- 2026-05-04: actual consumer checker 기준 `os_node::{...}` root import는 `main.rs`에서 `30`개, `tests/dev_cluster_daemons.rs`에서 `7`개, unique `34`개였다. 그중 `33`개가 `standalone_runtime.rs` public item과 직접 매치됐고 unmatched는 `NodeInfo` 하나뿐이었다. 따라서 `pub use standalone_runtime::*`는 현재 dead surface가 아니라 actively used public surface다. 다음 남은 질문은 `*` reexport가 정말 필요한지, 아니면 current consumer set을 기준으로 explicit export list로 줄일 수 있는지다.

- 2026-05-04: current repo에는 `use os_node::*` wildcard consumer가 없고, root consumer set은 explicit `34`개로 닫혀 있다. 그중 `33`개가 `standalone_runtime.rs` public item과 직접 매치되고 `NodeInfo` 하나만 non-standalone이다. 따라서 `pub use standalone_runtime::*`는 원칙적으로 current consumer set 기반 explicit export list로 대체 가능하다. 다음 남은 질문은 이 `33`개 explicit export list를 실제 patch candidate 형태로 생성하는 것이다.

- 2026-05-04: direct root path consumer까지 포함해 refined explicit export list는 `41`개 항목으로 늘어났고, 이를 실제 [`lib.rs`](/home/ubuntu/steelsearch/crates/os-node/src/lib.rs)에 적용한 뒤 `cargo build -p os-node --features standalone-runtime --bin steelsearch`와 `cargo test -p os-node --features standalone-runtime --test dev_cluster_daemons --no-run`가 모두 통과했다. 따라서 star reexport를 explicit export list로 바꾸는 functional patch candidate는 현재 consumer 기준으로 성립한다. 다음 남은 질문은 이 patch가 rebuild hotspot을 실제로 줄이는지다.

- 2026-05-04: star vs explicit tiny-leaf rebuild benchmark 3회 기준 `star=[3621,3615,3626]`, `explicit=[3544,3538,3594]`였고 median은 `3621ms -> 3544ms`로 `77ms` 개선됐다. 따라서 explicit export list patch는 rebuild hotspot에 measurable but modest win을 준다. 다음 남은 질문은 이 `77ms` 개선이 frontend hotspot 중 어떤 항목에서 나온 것인지다.

- 2026-05-04: nightly self-profile delta 비교에서 star vs explicit 간 대표 frontend hotspot 차이는 `expand_crate=-1.45ms`, `hir_crate=-0.55ms`, `late_resolve_crate=-0.17ms`, `expand_proc_macro=+0.10ms`, `incr_comp_encode_dep_graph=-0.01ms` 수준이었다. 즉 benchmark의 `77ms` 개선은 현재 관측한 대표 frontend hotspot 몇 개만으로는 설명되지 않는다. 다음 남은 질문은 이 개선이 stable `cargo --timings` section(frontend/codegen) 같은 build-mode-specific 구간에서 나오는지다.

- 2026-05-04: stable `cargo --timings` 비교에서도 star vs explicit 간 lib unit은 `duration=2.26s -> 2.26s`, `rmeta=1.87s -> 1.88s`, `post-rmeta=0.39s -> 0.38s`였다. 즉 section-level net delta는 사실상 `0ms`다. 따라서 earlier tiny-leaf benchmark의 `77ms` 개선은 current section-level evidence로는 재현되지 않으며, noise 가능성이 더 커졌다. 다음 남은 질문은 explicit export patch의 rebuild impact를 더 큰 sample size로 재검증했을 때도 stable하게 남는지다.

- 2026-05-04: Cargo 0.77.0 source + minimal fixture 기준으로 `unlocked_rmeta_units`는 `Build` mode `rlib -> rlib` edge에서만 채워진다. current repo graph에 그런 edge가 왜 없는지, 즉 `os-node`/`steelsearch` target 분해를 바꾸지 않고도 pipelined rmeta unlock을 만들 수 있는지 다음에 더 분리한다.

- 2026-05-04: current repo actual graph에서는 `os-node`를 소비하는 workspace library가 0개이고, `os-node` 내부 downstream도 `steelsearch` bin + tests뿐이라 `unlocked_rmeta_units`가 비는 구조가 확인됐다. 다음에는 `standalone_runtime` surface를 helper library로 떼는 식의 refactor가 실제 `Build` mode `rlib -> rlib` edge를 만들 수 있는지 따져야 한다.

- 2026-05-04: synthetic `runtime_surface -> os_node_facade -> app` fixture에서는 helper lib가 facade lib를 `unlocked_rmeta_units`로 실제 깨우는 것이 확인됐다. 따라서 current repo의 다음 질문은 가능성 자체가 아니라, 이 split이 실제 rebuild hotspot을 줄일 만큼 의미 있는지다.

- 2026-05-04: synthetic benchmark에서는 helper-lib split이 facade/root edit에는 median 424ms -> 194ms로 유의미한 이득이 있었지만, helper/runtime edit에는 median 426ms vs 439ms로 이득이 없었다. 다음에는 current repo의 실제 hot edit가 facade-like인지 helper-like인지부터 가려야 한다.

- 2026-05-04: current `os-node` actual rebuild에서는 `lib.rs` 3601ms, `standalone_runtime.rs` 3643ms, `write_path_invariants.rs` 3613ms로 helper-like edit가 root facade edit보다 싸지 않다. 다음에는 facade-only edit class가 current repo에서 실제로 얼마나 자주/중요한지부터 따져야 한다.

- 2026-05-04: facade-only edit class는 src 35개 파일 중 `lib.rs` 1개, 45060 lines 중 86 lines로 매우 작지만, root import surface 34개를 실제로 main/test가 소비한다. 다음에는 helper-lib split을 rebuild 성능 refactor로 볼지, root API surface/governance refactor로 볼지 분리해야 한다.

- 2026-05-04: current evidence를 합치면 helper-lib split은 현 시점 primary performance refactor보다는 root API surface/governance refactor에 더 가깝다. 다음 단계는 `standalone_runtime` export 41개 중 실제 helper-lib boundary 후보를 어디에 두는지다.

- 2026-05-04: helper-lib boundary의 1차 candidate는 current root consumer가 실제로 쓰는 active 33개다. 남은 8개 inactive export는 같이 이동할지, facade에 남길지, prune할지 따로 판단해야 한다.

- 2026-05-04: previous inactive tail 8개는 root import만 본 과소분류였고, corrected scan에서는 전부 `main.rs`의 qualified `os_node::...` path로 실제 사용된다. true tail은 0개이므로 다음 문제는 prune이 아니라 active export 41개를 어떤 coherent helper-lib subsets로 자를지다.

- 2026-05-04: active export 41개는 4 subset(tasking 6, coordination/membership 15, gateway/publication 13, rest/bootstrap/policy 7)으로 coherent하게 나뉜다. 다음에는 main-only이면서 더 작은 subset을 우선 extraction phase로 잡을 수 있는지 risk 순서를 정해야 한다.

- 2026-05-04: first extraction phase의 lowest-risk candidate는 `rest_bootstrap_and_policy`다. `main.rs` 단일 consumer, export 7개, reference hits 7로 가장 작고 고립돼 있다. 다음에는 이 subset을 실제 helper-lib patch candidate 구조로 스케치해야 한다.

- 2026-05-04: `rest_bootstrap_and_policy` first extraction은 one-shot 7-symbol move가 아니라 2-phase split으로 잡아야 한다. 즉 phase1 thin core 5개를 먼저 분리하고, `SteelNode`와 `serve_rest_http_listener_until`는 adapter boundary 뒤 phase2로 미루는 편이 더 안전하다.

- 2026-05-04: phase1 thin-core helper crate `os-node-rest-core` scaffold는 실제 workspace member/dependency로 올렸고, `steelsearch` bin build와 `os-node --all-targets` check까지 통과했다. 다음에는 이 real scaffold가 facade/root edit rebuild cost를 실제로 줄이는지 current repo에서 재야 한다.

- 2026-05-04: real phase1 scaffold는 governance scaffold로는 성립했지만, `os-node/src/lib.rs` median 3601ms -> 3614ms라 root edit 성능 개선은 없었다. 성능 이득을 원하면 crate 내부 thin-core split보다 `os-node` crate 자체를 더 강하게 분리하는 구조를 따져야 한다.

- 2026-05-04: warm `cargo build -vv` probe에서 `os-node-rest-core`는 fresh인데 `os-node` giant lib unit만 dirty/compile되었다. 즉 성능 이득을 원하면 thin-core helper보다 더 큰 crate boundary가 필요하고, 다음 질문은 그 경계를 `standalone_runtime` giant body 쪽에 둘지 facade crate 쪽에 둘지다.

- 2026-05-04: stronger split의 lowest-risk candidate는 small facade 추가 분해가 아니라 `standalone_runtime` giant body를 facade 뒤 helper crate로 넘기는 방향이다. 다음 단계는 그 stronger scaffold patch candidate를 어떤 단위로 잡을지다.

- 2026-05-04: stronger scaffold의 현실적 closure는 `standalone_runtime.rs` 단독이 아니라 direct route-registration 25개(6302 lines) + `NodeInfo` resolution까지 포함한 `os-node-runtime` crate다. 다음에는 이 stronger scaffold를 실제 patch candidate로 만들지, 아니면 여기서 설계 결론으로 멈출지 판단해야 한다.

- 2026-05-04: `os-node-runtime` stronger scaffold는 27 files / 35053 lines scope라 low-risk next patch candidate로 보기 어렵다. 다음에는 이 branch를 design conclusion에서 멈추게 하는 go/no-go gate를 문서화해야 한다.

- 2026-05-04: `probe_java_rust_mixed_membership.sh` actual run에서 `membership_timeout + blocker_class=standalone_only_bootstrap`는 안정적으로 재현됐지만, 같은 report의 `observed_node_count`는 이번 artifact `/tmp/java-rust-mixed-membership.0RA3oY`에서 `0`으로 찍혔다. blocker 해석과는 별개로 timeout 시점 `current_node_count()` snapshot race인지, Java node liveness 자체가 timeout 직전 흔들린 것인지 나중에 따로 분리할 가치가 있다.
- mixed delayed artifact만으로는 followup `connectToNode()`가 `connectionValidator.validate(...)` 이전에 실패하는지, 아니면 `connectedNodes.putIfAbsent(...)`/`onNodeConnected(...)` 이후 곧바로 peer close로 빠지는지 아직 구분되지 않는다.
- delayed mixed artifact에서는 `start_join` 26개 중 21개가 live `internal:transport/handshake` full-connect channel과 동시 존재하므로, 남은 모호성은 `candidate channel이 먼저 죽는가`보다는 `connectedNodes` 등록 전 실패인지, 등록은 됐지만 profile/type mismatch로 reuse 대상이 아닌지다.
- `TransportService.sendRequest(node, ...) -> getConnection(node) -> NodeChannels.sendRequest(...)` 경로에서는 새 TCP socket을 열지 않으므로, fresh `start_join` socket은 registered connection reuse가 아예 일어나지 않았음을 시사한다. 남은 모호성은 validate 이전 실패인지, connectedNodes 등록 직후 즉시 unregister인지다.
- followup `connectToNode()` validator는 `internal:transport/handshake`이며 failure branch는 즉시 `conn`을 닫는다. delayed artifact의 full-connect sockets가 handshake response 뒤 ~0.7s 살아 있다는 점은 validate 이전 실패보다 post-validation loss를 더 시사한다. 남은 모호성은 `connectedNodes.putIfAbsent(...)` 전후 어느 지점에서 사라지느냐다.
- delayed mixed artifact의 `internal:discovery/request_peers` 48건은 `connectToRemoteMasterNode(...).onResponse -> discoveryNode.set(remoteNode); requestPeers();` source contract상 followup `connectToNode()` 성공 이후에만 가능하다. 따라서 남은 모호성은 등록 전 실패가 아니라, 등록 성공 후 왜 `start_join/publish_state` 전까지 connection이 사라지느냐다.
- `NodeChannels`는 멀티채널이고 default profile은 `REG`를 포함한 여러 sibling channel을 함께 연다. delayed artifact에서 `internal:transport/handshake`와 `request_peers/start_join` first-frame socket이 같은 tick에 함께 열리는 경우가 많아, fresh first-frame socket 자체만으로 whole-connection unregister를 주장하면 과도하다. 남은 질문은 registered multi-channel sibling lifecycle 안에서 왜 handshake channel만 먼저 닫히는지다.
- 현재 mixed path의 핵심은 whole connection loss보다 multi-channel sibling skew다. `request_peers/start_join`는 REG sibling, `publish_state`는 STATE sibling으로 실려 가는 반면, handshake에 쓰인 REG channel은 same-socket follow-up 없이 idle sibling으로 남아 먼저 닫히는 모양이다. 남은 질문은 왜 peer가 그 idle handshake-used REG channel을 약 0.7~0.8s band에서 먼저 닫느냐다.
- current mixed shape는 `REG=6` round-robin sibling rotation과 잘 맞는다. validator handshake가 한 REG sibling을 먼저 쓰고, 이후 `request_peers/start_join`가 다른 REG sibling으로 회전하면서 handshake-used channel만 idle로 남는 모양이다. 남은 질문은 왜 그 idle sibling이 정확히 `~0.7~0.8s` band에서 peer-side close되느냐다.
- idle handshake-used REG sibling의 close band `707ms~803ms`는 current source에서 드러나는 named high-level timers(1000ms, 3000ms)와 clean match가 아니다. 남은 질문은 lower transport cleanup인지 Netty/socket-layer timer인지다.
- current source scan에서는 `TcpTransport`의 explicit scheduled close는 connect-timeout뿐이고, `transport-netty4`에도 `IdleStateHandler`/`ReadTimeoutHandler`/`WriteTimeoutHandler`가 없다. 그래서 idle handshake-used sibling close band `707ms~803ms`의 직접 source는 Java source에 드러난 explicit timer보다 peer-side socket/cleanup behavior 쪽이 더 가깝다.
- `JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_TCP_TRANSPORT_LOG_LEVEL=DEBUG` actual probe에서 `TcpTransport.ChannelCloseLogger` close-age trace가 실제로 찍히고, `rust-replica-1` 대상 age가 `700ms~850ms` band로 관측된다. 남은 질문은 이 band 중 어떤 close가 idle handshake-used REG sibling인지, 그리고 age 0ms immediate close와 어떻게 분리되는지다.
- `TcpTransport.ChannelCloseLogger` trace 기준으로 `age 0ms` immediate close는 address-only probe node class, `700ms~850ms` band는 named rust full-connection class에 주로 몰린다. 남은 질문은 named-rust class 내부에서 어떤 close가 idle handshake-used REG sibling인지다.
- `named rust full-connection` close-age는 단일 집합이 아니라 `~800ms` dominant mode, `~600ms` secondary mode, `2004ms` outlier로 갈린다. 남은 질문은 `~800ms` dominant mode가 실제 idle handshake-used REG sibling인지 여부다.
- named-rust `~800ms` dominant mode `57건`은 delayed mixed capture의 `internal:transport/handshake` candidate `26개`보다 많다. 따라서 이 dominant mode 전체를 idle handshake-used REG sibling 순수 subset으로 보기는 어렵고, 다른 REG/STATE sibling close가 섞여 있다. 남은 질문은 stricter subset을 가를 추가 signal이다.
- named-rust `~800ms` dominant mode 안에서 stricter subset을 가르는 현재 최선 signal은 same-report port correlation이다:
  - Java `opened transport connection ... using channels [localAddress=...]`
  - Rust `internal:transport/handshake` first-frame `peer_addr`
  - 다만 이게 action class 차이(REG handshake sibling vs other REG/STATE sibling)까지 직접 증명하는지는 아직 별도 검증이 필요하다.
- latest TRACE 기준으로는 action class 검증도 절반은 닫혔다:
  - handshake-port subset `23/23`은 모두 `internal:transport/handshake` signal을 가진다.
  - non-handshake-port `32건`은 `internal:transport/handshake`가 `0/32`다.
  - 하지만 `28/32`는 capture된 action-bearing port가 전혀 없어, 정확히 어느 REG/STATE sibling action class인지까지는 아직 비어 있다.
- blind `28건`도 Java TRACE만 보면 완전히 비어 있지는 않다:
  - `observed close on channelIndex`
  - source-derived default profile offset
  를 합치면 `REG=6`, `STATE=1` 같은 typed index footprint는 복원된다.
  - `selected channel index ... from handle types ...` TRACE는 actual probe에 이미 실을 수 있음이 확인됐다.
  - latest actual parse에서는 REG selection이 `singleton index0 probe family`와 `multichannel 7..12 round-robin family`로 갈린다.
  - 하지만 `ConnectionProfile TRACE + TransportService.tracer include` actual probe에서도 target action literal은 `0건`이라, current available logs만으로는 multichannel `7..12` family의 action별 cadence attribution이 안 된다.
  - current decision은 built-in tracer debugging보다 action-tagged selected-index instrumentation이 더 직접적이라는 쪽이다.
  - minimal patch surface는 `ConnectionProfile.getChannel(...)`보다 `TcpTransport.NodeChannels.sendRequest(...)`가 더 낫다. 여기서는 `requestId`, `action`, `options.type()`, selected `TcpChannel`이 한곳에 모인다.
  - `OPENSEARCH_FORCE_GRADLE_RUN=1` probe artifact에서는 새 action-tagged line이 `0건`이었지만, install-tree class overlay로 patched `TcpTransport`/`NodeChannels`를 강제로 주입하자 `action-tagged selected channel index` line `560건`이 실제로 표면화됐다.
  - latest parse에서는 `follower_check -> PING index 3`, `publish_state -> STATE index 4`, `request_peers/request_pre_vote/start_join -> REG 7..12`, `transport/handshake -> REG index0 singleton + REG 7..12 followup`까지 actual cadence attribution이 열렸다.
  - 남은 질문은 REG `7..12` family 내부 index skew가 왜 완전 균등하지 않은지다.
- mixed Java/Rust overlay artifact에서 REG `7..12` skew 자체는 `persistent round-robin counter + variable request_peers multiplicity`로 닫혔지만, 왜 cycle별 `request_peers` multiplicity가 `1..4`로 흔들리는지는 아직 남아 있다. 다음으로는 PeerFinder/connector round overlap이나 connect epoch 재진입이 같은 cycle 안의 추가 `request_peers`를 만드는지 source/runtime 양쪽에서 더 봐야 한다.
- 현재 evidence는 `request_peers` multiplicity의 직접 원인을 `1s wakeup`보다 `address-keyed overlapping Peer -> same DiscoveryNode convergence` 쪽으로 좁힌다. 남은 질문은 이 추가 Peer fanout이 주로 `configuredHosts`, `cluster_manager_node`, `knownPeers` 중 어디에서 오는지다.
- current 2-node fixture에서는 listed trio 중 primary non-local fanout source가 `configuredHosts`로 좁혀졌다. 남은 질문은 이 configuredHosts-origin probe가 왜 반복 재시도되는지, 즉 `findPeersInterval` wakeup인지 `handlePeersRequest()` 반사 probe인지 `connection close -> immediate reprobe`인지다.
- repeated reprobe의 direct trigger는 current evidence상 `findPeersInterval` wakeup으로 좁혀졌다. 남은 질문은 singleton reprobe cadence의 `857ms min / 1681ms max` outlier가 scheduler jitter인지, close timing과 wakeup phase difference 때문인지다.
- singleton reprobe cadence outlier는 now `close-to-next-wakeup phase difference`로 좁혀졌다. 남은 질문은 named-rust close-age mode가 왜 `~600ms`와 `~800ms`로 갈리는지, 즉 shorter-lived connection branch가 무엇인지다.
- named-rust close-age split은 now `publication fast-fail branch (~600ms)` vs longer post-publication dwell branch (`~800ms`)로 좁혀졌다. 남은 질문은 이 fast-fail timing 차이가 `FollowersChecker` fault escalation timing인지, `Publication` failure propagation timing인지다.
- fast-fail timing split은 now `FollowersChecker disconnected/marking_faulty timing` 쪽으로 더 좁혀졌다. 남은 질문은 왜 어떤 cycle에서는 `publish_state` 후 ~359ms에 fault escalation이 오고, 다른 cycle에서는 ~496ms까지 늦어지는지다.
- `FollowersChecker` timing split은 now scheduling보다 `follower_check send -> disconnected` response/close path 쪽으로 더 좁혀졌다. 남은 질문은 `375ms` vs `504ms` 차이가 remote EOF arrival timing인지, FollowersChecker retry/timeout 내부 path인지다.
- `FollowersChecker` split은 now retry/timeout 내부 path가 아니라 `remote EOF/disconnect arrival timing` 쪽으로 좁혀졌다. 남은 질문은 rust side close trigger가 publication/follower path의 어떤 sub-branch에서 더 빨리 도달하느냐이다.
- current source+artifact 기준으로 Rust side explicit timeout/active close branch는 배제됐다. 남은 질문은 Java side에서 remote EOF/disconnect를 더 빨리 만드는 sub-branch가 `FollowersChecker failNode` fast path인지, publication failure 이후 transport close path인지다.
- Java side `FollowersChecker failNode`는 now disconnect 이후의 reactive cleanup path로 좁혀졌다. 남은 질문은 upstream Java transport close/publication-side path 안에서 무엇이 `~375ms` vs `~504ms` split을 만드는지다.
- `publication failure / failed to join` logging도 now 대체로 transport close downstream signal로 좁혀졌다. 남은 질문은 upstream Java transport close 자체를 더 이르게 만드는 path가 무엇인지다.

- `shared connection teardown caller` 가설은 약해졌다. 남은 질문은 이제 coordination/discovery 상위 caller가 아니라 lower transport channel close의 peer-side upstream source가 publication response handling 직후 close인지, shared connection idle/cleanup인지다.

- `publication 직후 immediate close` 가설은 약해졌다. 남은 질문은 shared connection idle/cleanup 안에서도 state channel 자체 inactivity인지, connection-level sibling teardown 연쇄인지다.

- `state channel only inactivity` 가설은 약해졌다. 남은 질문은 sibling teardown cascade 안에서 실제 first closer가 handshake-used REG idle sibling인지, PING/STATE sibling인지다.

- current first closer는 `PING/STATE`보다 handshake-used REG idle sibling 쪽으로 좁혀졌다. 남은 질문은 peer-side에서 이 first close가 왜 node connection 전체 sibling cascade로 번지는가다.

- `first closer = handshake-used REG`는 현재 evidence와 맞지 않는다. 현 단계에서는 `PING/STATE`는 배제되고, earliest index distribution이 `0` 중심 low-index sibling family로 몰린다는 점만 고정된다.

- named-rust only 기준 earliest index distribution은 `1:34, 2:13, 6:13, 7:6, 5:4, 9:2, 10:2`다. `index 0` 우세는 address-only probe connection이 섞였을 때 생기는 착시였다.

- Java-side whole-connection teardown owner는 `TcpTransport`의 per-channel close listener -> `nodeChannels.close()` fanout으로 좁혀졌다. 남은 질문은 왜 low-index sibling family(1/2/6)가 first closer로 치우치느냐이다.

- `1/2/5/6` skew는 active BULK/RECOVERY traffic pressure보다 unused idle sibling pressure와 더 잘 맞는다. 남은 질문은 왜 idle low-index sibling이 peer-side에서 먼저 닫히느냐, 특히 open order/last accessed 차이와 연결되는가이다.

- 현재 first-close skew는 keepalive보다 `unused idle sibling stale-access`와 더 잘 맞는다. 남은 질문은 stale siblings 중에서도 왜 `1/2/6`이 더 먼저 닫히느냐이다.

- `index 0`은 truly idle low-index set이 아니라 bring-up handshake channel이라 first-close skew 설명 대상에서 제외된다. 남은 질문은 true idle set `1/2/5/6` 내부에서 왜 `1/2/6`이 `5`보다 훨씬 먼저 닫히느냐이다.

- true idle set 내부 skew는 simple open-order monotonic rule과 맞지 않는다. 남은 질문은 peer implementation detail을 보려면 Java-side channel metadata나 Netty/peer close ordering을 더 수집해야 하는가이다.

- current built-in signal은 structure 파악에는 충분하지만 peer detail을 닫기엔 `isServerChannel`, close cause, lastAccessed age`가 비어 있다. 남은 질문은 minimal patch로 `isServerChannel + lastAccessed age`면 충분한지다.

- current next step은 Netty close cause dig보다 `ChannelCloseLogger`에 `isServerChannel + lastAccessed age`를 넣는 minimal patch다. 남은 질문은 이 patch로 idle low-index first-close가 client-side stale sibling인지 실제로 닫히는가이다.

- `serverChannel=false + idleForMs≈801ms`로 보아 low-index first-close는 client-side stale sibling이다. 남은 질문은 왜 이 client-side stale sibling close가 600~800ms band에서 오느냐이다.

- `600ms~800ms` stale-sibling band는 `peer half-close`보다 Java client-side close로 읽는 편이 더 맞다. 남은 질문은 이 close를 실제로 일으키는 Java-side higher-level policy/timer path가 무엇인지다.

- `TransportKeepAlive`는 current source에서 stale channel close를 하지 않는다. 따라서 남은 질문은 higher-level Java policy가 아니라 lower transport/socket layer direct cause다.

- lower transport direct cause는 existing Netty close-hint path로 이미 좁혀졌다. 남은 질문은 이 hint trace를 actual probe stdout에 어떻게 surface하느냐이다.

- Netty close hint trace는 actual probe stdout에 surface됐다. 남은 질문은 low-index stale sibling close에 실제로 어떤 hint가 붙는가이다.

- low-index stale sibling close는 surfaced Netty hint에서도 거의 전부 `unknown`이다. 남은 질문은 `recordCloseHint` / `closeFutureIntercepted` 주변에 어떤 extra cause metadata를 넣어야 unknown을 줄일 수 있는가이다.

- `unknown`을 줄이는 최소 patch surface는 broad Netty dig가 아니라 `Netty4TcpChannel.close()` 직전 explicit local-close hint 추가로 좁혀졌다. 남은 질문은 이 patch가 실제로 unknown 비율을 줄이는가이다.
- 2026-05-04: `Netty4TcpChannel.close()`에 `recordCloseHint("explicitLocalClose", null)` patch를 실제로 넣고 `:modules:transport-netty4:compileJava`까지 통과시켰다. 그러나 actual probe에서 patched class를 runtime에 싣는 단계가 packaging/class-loading blocker에 걸렸다. `Netty4TcpChannel.class`를 overlay로 주입하면 OpenSearch startup이 `jar hell`(`modules/transport-netty4/transport-netty4-client-3.7.0-SNAPSHOT.jar` vs `lib/opensearch-3.7.0-SNAPSHOT.jar`)로 실패했고, install-tree jar 직접 patch도 동일하게 startup을 깨뜨렸다. 따라서 다음 질문은 `unknown` 비율 감소 자체보다, `Netty4TcpChannel` patched class의 true runtime packaging target과 jar hell 없이 probe에 태우는 최소 주입 경로가 무엇인지다.
- 2026-05-04: `run-opensearch-dev.sh`를 확인한 결과 `CLASS_OVERLAY_*`는 항상 `lib/opensearch-3.7.0-SNAPSHOT.jar`에 `jar uf` 하고, `EXTRA_JAR_OVERLAY_SPECS`만 explicit jar target을 허용한다. 따라서 script-level 최소 주입 경로는 `TcpTransport -> CLASS_OVERLAY(lib)` + `Netty4TcpChannel -> EXTRA_JAR_OVERLAY_SPECS(module)`의 split-target path다. 그러나 current install tree를 same probe로 확인하면 `transport-netty4-client.jar`와 `lib/opensearch-3.7.0-SNAPSHOT.jar` 둘 다 `Netty4TcpChannel.class`를 포함하고 있고, 실제 startup도 이 두 jar pair로 `jar hell`에 막힌다. 남은 질문은 이 dual-jar presence가 pristine baseline packaging인지, 아니면 이전 실험 오염인지다.
- 2026-05-04: `:distribution:archives:linux-arm64-tar:assemble`로 pristine tarball을 만들고 확인한 결과 `Netty4TcpChannel.class`의 baseline owner는 module jar(`modules/transport-netty4/transport-netty4-client-3.7.0-SNAPSHOT.jar`)이며 `lib/opensearch-3.7.0-SNAPSHOT.jar`에는 없다. current install tree도 assemble 후 다시 `module=true, lib=false`로 돌아왔다. 따라서 earlier dual-jar presence는 baseline packaging이 아니라 이전 overlay/jar patch 실험 오염이었다. 또한 clean install tree에서 `TcpTransport -> CLASS_OVERLAY(lib)` + `Netty4TcpChannel -> EXTRA_JAR_OVERLAY_SPECS(module)` split-target path를 actual probe로 태우면 startup이 통과하고 blocker가 `membership_timeout`으로 내려오며, low-index first-close hint도 `explicitLocalClose=65, unknown=1`로 바뀐다. 남은 질문은 왜 `unknown=1`이 여전히 남는지, 즉 `Netty4TcpChannel.close()`를 거치지 않는 별도 close path가 있는지다.
- 2026-05-04: clean split-target artifact에서 low-index first-close `unknown=1`(port `54474`, index `6`)은 distinct close path보다 listener ordering race 쪽과 더 잘 맞는다. 실제 로그에서 `netty4 tcp channel close completed ... hint[unknown]`가 먼저 찍히고, 11 lines later에 같은 port의 `Netty4MessageChannelHandler.channelInactive`가 뒤따른다. 또한 current artifact에는 `SecureNetty4Transport` dual-mode raw `ch.close()` error literal이나 `server/src/main/java/org/opensearch/transport` raw `channel.close()` warn 흔적이 없다. 남은 질문은 low-index가 아닌 다른 `unknown`도 같은 race로 설명되는지다.
- 2026-05-04: clean split-target artifact의 node-connection scoped non-low-index `hint[unknown]`는 `10건`이며, 그중 `9건`은 50-line window 안에서 같은 port의 `Netty4MessageChannelHandler.channelInactive`가 뒤따라 ordering race로 설명된다. 다만 `connection_id=8, index=9, port=54214, closeOrder=49` 한 건은 같은 window에서 `channelInactive`가 안 보여 residue로 남는다. 남은 질문은 이 1건이 더 늦은 `channelInactive`인지, 아니면 실제 distinct close path인지다.
- 2026-05-04: residue로 남았던 `connection_id=8, index=9, port=54214`도 distinct close path가 아니라 늦은 ordering race였다. same artifact 전체에서 이 port는 4번만 나오고, `hint[unknown]` 이후 68 lines later에 같은 port의 `Netty4MessageChannelHandler.channelInactive`가 실제로 관측된다. 따라서 current clean artifact의 unknown들은 close path residue보다 `close trace before channelInactive` ordering race로 보는 편이 맞다. 남은 질문은 source-level로 이 race를 어떻게 줄이거나 없앨지다.
- 2026-05-04: source checker 기준 minimal race-fix surface는 새 close-path marker 추가가 아니라 `Netty4TcpChannel.installCloseTraceListener()` ordering/deferral 변경이다. `Netty4Transport`는 early-close hint handler와 `Netty4MessageChannelHandler.channelInactive`를 이미 두고 있고, 현재 문제는 `installCloseTraceListener()`가 close-future 시점에 attr을 한 번만 읽어 TRACE를 먼저 찍는다는 점이다. 따라서 다음 남은 질문은 이 listener를 실제로 지연시키거나 hint를 재조회하도록 바꿨을 때 clean split-target probe에서 `hint[unknown]`가 0으로 떨어지는지다.
- 2026-05-04: `Netty4TcpChannel.installCloseTraceListener()`의 close TRACE를 `eventLoop().execute(...)`로 한 tick 미루는 patch를 실제로 넣고 clean split-target probe(`/tmp/java-rust-mixed-membership-close-trace-deferral.latest.json`)를 돌렸지만 `hint[unknown]`는 없어지지 않았다. low-index는 `unknown=2`로 오히려 1건 늘었고, 두 건 모두 같은 port의 `channelInactive`가 1 lines later, 5 lines later에 뒤따랐다. non-low-index `unknown=9`도 대부분 race였고, residue처럼 보인 `port=60374`도 전체 검색에서는 `channelInactive`가 76 lines later에 나타났다. 따라서 한 tick deferral만으로는 부족하고, 다음 남은 질문은 close TRACE를 아예 `channelInactive` path에서 직접 찍을지, 아니면 close-future listener가 `unknown`일 때 더 늦게 hint를 재조회하는 stronger ordering patch가 필요한지다.
- 2026-05-04: stronger ordering patch로 `Netty4MessageChannelHandler.channelInactive()`에서 `tcpChannel.emitCloseTraceIfNeeded()`를 직접 호출하고, close-future 쪽은 fallback으로만 남기자 clean split-target probe(`/tmp/java-rust-mixed-membership-channelinactive-trace.latest.json`)에서 low-index `unknown=0`, non-low-index `unknown=0`이 됐다. 즉 current unknown race는 `channelInactive`-first emit으로 실질 해소된다. 남은 질문은 이제 race 자체가 아니라, unknown-free artifact에서 `explicitLocalClose`와 `channelInactive`가 action/channel family별로 어떻게 분포하는지가 stale-sibling close model을 어떻게 더 좁히는지다.
- 2026-05-04: unknown-free clean artifact를 action/channel family별로 다시 집계하면 named node first-close `75건` 중 `74건`이 `explicitLocalClose`이고, action-bearing selected family(`PING/STATE/REG`)도 전부 `explicitLocalClose`다. 즉 current stale-sibling close model은 `channelInactive` 지배가 아니라 `client-side explicitLocalClose` 지배로 더 좁혀진다. 남은 예외는 `connection_id=2, index=7, port=51494`의 `closeFutureIntercepted` 1건뿐이며, 실제 로그에서도 같은 port의 `channelInactive`보다 한 줄 먼저 찍힌다. 다음 질문은 이 lone outlier가 `Netty4Transport.addEarlyCloseFutureHintListener`의 early close path인지다.
- 2026-05-04: lone non-explicit outlier(`connection_id=2, index=7, port=51494`)는 source/actual 대조상 `Netty4Transport.addEarlyCloseFutureHintListener()` path와 가장 잘 맞는다. source에는 hint-null이면 `closeFutureIntercepted`를 채우는 early close-future listener가 있고, actual artifact에서도 same-port `closeFutureIntercepted`가 `Netty4MessageChannelHandler.channelInactive`보다 1 line 먼저 찍힌다. 남은 질문은 이 1건까지 없애기 위해 early listener 자체를 조정할 가치가 있는지, 아니면 current stale-sibling close model에는 benign residue로 남겨도 되는지다.
- 2026-05-04: current clean artifact 기준 first-close hint는 `explicitLocalClose=74`, `closeFutureIntercepted=1`이고 residue 비율은 `1/75 = 1.33%`다. 동시에 action-bearing selected channels의 hint는 전부 `explicitLocalClose`다. 따라서 current stale-sibling close model을 설명하는 데서 lone early-listener residue 1건은 benign residue로 보는 편이 맞다. 남은 질문은 이 Netty close-hint branch 결론을 어떻게 decision note로 묶고 mixed-membership blocker 본류로 복귀할지다.
- 2026-05-04: Netty close-hint branch decision note를 `docs/rust-port/netty-close-hint-branch-decision-note.md`로 기록했다. 이 branch의 현재 결론은 `unknown` race는 source-level ordering issue였고, stronger patch로 clean probe에서 해소되며, lone `closeFutureIntercepted` 1건은 benign residue라는 것이다. 남은 질문은 더 이상 Netty hint branch 내부가 아니라, latest actual mixed-membership artifact 기준 non-Netty mainline blocker를 어떻게 다시 restage할지다.
- 2026-05-04: latest actual mixed-membership artifact(`/tmp/java-rust-mixed-membership-channelinactive-trace.latest.json`)로 mainline을 다시 세우면, 상태는 여전히 `failure_stage=membership_timeout`, `membership_formed=false`, `success_path_ready=false`다. mixed path action count도 `publish_state=1`, `commit_state=0`이므로 Netty close-hint branch를 닫고 돌아온 뒤의 current first unresolved mainline blocker는 여전히 `publish_state 이후 commit_state 미진입` 경로다. 남은 질문은 이제 commit_state path 구현/분리 쪽 본류 작업으로 어떻게 복귀할지다.
- 2026-05-04: `main.rs`에 first-frame `internal:cluster/coordination/commit_state` 응답 경로를 실제로 추가하고 latest probe(`/tmp/java-rust-mixed-membership-commit-state-firstframe.latest.json`)를 다시 돌렸지만 상태는 그대로 `failure_stage=membership_timeout`, `membership_formed=false`, `publish_state=1`, `commit_state=0`이다. 즉 current blocker는 Rust가 first-frame commit_state에 응답하지 못해서가 아니라 Java 쪽이 commit_state를 아예 보내지 못하는 upstream precondition에 더 가깝다. 남은 질문은 publish_state 이후 어떤 precondition이 빠져 Java가 commit_state send를 생략하는지다.
- 2026-05-04: source/actual 대조 결과 `commit_state`는 `CoordinationState.handlePublishResponse()`가 publish quorum을 인정해 `ApplyCommitRequest`를 만들 때만 나가고, publish 응답은 `PublicationTransportHandler`에서 `PublishWithJoinResponse(in)`으로 읽힌다. latest probe stdout에는 `handlePublishResponse: accepted publish response`, `value committed`, `publish response from`이 모두 `0건`이고 `failed to commit cluster state`만 `73건`이다. 따라서 current first unresolved mainline blocker는 first-frame commit_state handler 부재가 아니라 Rust의 current `publish_state` 응답이 Java 쪽 `PublishWithJoinResponse` acceptance/quorum precondition으로 이어지지 않는 점이다. 남은 질문은 이 응답의 어떤 semantic/serialization mismatch가 acceptance를 막는지다.
- 2026-05-04: `build_publish_with_join_response()`는 이미 fallback raw wire보다 `try_build_java_publish_with_join_response()`를 우선 쓰고, helper script도 실제 Java `PublishWithJoinResponse(PublishResponse, Optional.of(Join))` 객체를 serialize한다. 그럼에도 latest probe에서는 `accepted publish response=0`, `value committed=0`, `failed to commit cluster state=73`이 계속된다. 따라서 current blocker는 Java-compatible wire builder 부재가 아니라 generated `PublishWithJoinResponse` 내부 `Join`/vote/quorum semantics mismatch 쪽으로 더 좁혀진다. 남은 질문은 generated `Join`의 `source/target/lastAcceptedTerm/lastAcceptedVersion` 중 무엇이 Java 기대와 어긋나는지다.
- 2026-05-04: current source chain상 generated `Join`의 가장 유력한 mismatch field는 `lastAcceptedVersion`이다. Rust `publish_state` branch는 응답 전에 `coordination_state.last_accepted_term/version = term/version`으로 새 publish 값을 반영하고, helper script는 그 값을 그대로 `Join(localNode, seedNode, term, lastAcceptedTerm, lastAcceptedVersion)`에 넣는다. 하지만 Java `CoordinationState.handleJoin()`는 `join.lastAcceptedTerm == local lastAcceptedTerm && join.lastAcceptedVersion > local lastAcceptedVersion`이면 join을 reject하며, `Publication.PublishResponseHandler`는 join 처리 뒤에야 publish response acceptance로 진행한다. 남은 질문은 generated Join이 fresh publish version 대신 pre-publish `lastAcceptedVersion`을 광고하도록 바꾸면 실제 acceptance/quorum이 열리는지다.
- 2026-05-04: generated Join이 fresh publish version 대신 pre-publish `lastAcceptedVersion`을 광고하도록 실제로 바꾸면 publish response `body_hex`는 분명히 달라지지만, latest probe(`/tmp/java-rust-mixed-membership-prepublish-join.latest.json`)에서는 여전히 `accepted publish response=0`, `value committed=0`, `failed to commit cluster state=76`이다. 따라서 `lastAcceptedVersion` freshness는 current blocker의 일부 후보였지만 단독 원인은 아니다. 남은 질문은 generated `Join`의 `sourceNode/targetNode` 또는 wider vote semantics가 Java 기대와 어긋나는지다.
- 2026-05-04: source checker 결과 generated `Join`의 source/target direction 자체는 Java contract와 맞다. `Join` source comment는 vote provider, target comment는 vote target을 명시하고, `Join.targetMatches()`는 target node id만 비교하며, `VoteCollection.addJoinVote()`는 `join.getSourceNode()`의 `nodeId`로 vote를 모은다. Rust helper script도 실제로 `Join(localNode, seedNode, ...)`를 만든다. 따라서 current blocker를 source/target direction mismatch로 보기는 어렵다. 대신 `DiscoveryNode.equals/hashCode`가 `ephemeralId` 기준이라는 점 때문에 다음 남은 질문은 generated `sourceNode` identity, 특히 `ephemeralId` semantics가 Java discoveryNode/vote 기대와 어긋나는지다.
- 2026-05-04: source checker 결과 basic `sourceNode` identity mismatch 가능성도 낮다. Rust는 transport handshake identity와 publish `Join.sourceNode` 둘 다 같은 `transport_identity` (`node_id`, `ephemeral_id`, roles)를 재사용하고, helper script도 같은 local ephemeral id를 넣는다. Java `Publication`은 `discoveryNode.equals(join.getSourceNode())`를 assert하며, `DiscoveryNode.equals/hashCode`는 `ephemeralId` 기준이다. current source상 이 basic identity는 handshake/publish 사이에서 일관되고, Rust default roles도 `cluster_manager`를 포함하므로 `VoteCollection.addVote()`의 cluster-manager gate도 basic level에서는 통과 방향이다. 따라서 다음 남은 질문은 basic identity가 아니라 Java `CoordinationState.handleJoin` rejection reason 또는 publication-side failure reason을 actual/probe artifact에서 직접 surface해 remaining wider semantic mismatch를 분리하는 것이다.
- 2026-05-04: probe wrapper에 `OPENSEARCH_COORDINATIONSTATE_LOG_LEVEL`, `OPENSEARCH_PUBLICATION_LOG_LEVEL` pass-through를 추가하고 actual probe(`/tmp/java-rust-mixed-membership-join-rejection-trace.latest.json`)를 다시 돌렸지만, `handleJoin:*`, `publish response from ... contained no join`, `failed to commit cluster state`는 모두 `0건`이었다. 즉 current blocker는 단순 logger knob 미노출이 아니라, existing logger settings만으로는 Java rejection reason이 probe stdout에 surface되지 않는다는 점이다. 다음 남은 질문은 `CoordinationState.handleJoin`/`Publication` rejection path에 direct instrumentation을 넣을지, 아니면 current log4j wiring에서 이 category가 왜 stdout에 안 뜨는지 더 분리할지다.
- 2026-05-04: source/actual checker 결과 direct instrumentation이 다음 최소 경로다. latest probe에서는 logger knob를 열어도 `handleJoin:*` / `publish response from ... contained no join`가 모두 `0건`이지만, source에는 `CoordinationState.handleJoin` reject site와 `Publication` missing-join path가 이미 명시적으로 존재한다. 따라서 다음 남은 질문은 log4j wiring 재탐색이 아니라, `CoordinationState.handleJoin` reject class 또는 `Publication` missing-join/failure class를 actual probe stdout에 남기는 최소 direct instrumentation patch를 어디에 둘지다.
- 2026-05-04: `CoordinationState.handleJoin` reject branch와 `Publication.PublishResponseHandler` missing-join/onFailure path에 `steelsearch_*` WARN marker를 실제로 넣고 `:server:compileJava` 후 class overlay probe(`/tmp/java-rust-mixed-membership-direct-join-rejection.latest.json`)를 재실행했지만 marker는 전부 `0건`이었다. 따라서 current blocker는 semantic rejection class가 무엇인지보다, patched `CoordinationState`/`Publication` path가 actual probe에서 정말 hit/loaded 되는지, 혹은 failure가 이 reject paths보다 더 upstream에서 끝나는지다. 다음 남은 질문은 unconditional entry marker를 더 앞단에 넣을지, 아니면 class overlay load 자체를 더 검증할지다.
- 2026-05-04: `Publication.PublishResponseHandler.onResponse`와 `CoordinationState.handleJoin` entry에 unconditional `steelsearch_*_entry` WARN marker를 추가하고 class overlay probe(`/tmp/java-rust-mixed-membership-publication-entry.latest.json`)를 재실행했지만 entry marker도 `0건`이었다. 따라서 current next question은 semantic rejection class가 아니라, patched `Publication`/`CoordinationState` classes가 actual probe에서 정말 load되는지, 아니면 publish response path가 Java server classes에 도달하기 전 upstream transport/client path에서 끝나는지다.
- 2026-05-04: `CoordinationState`/`Publication` static class-load canary probe(`/tmp/java-rust-mixed-membership-class-load-marker.latest.json`)의 report JSON embedded stdout/stderr만 보면 marker가 `0건`처럼 보였지만, same-run raw log(`/tmp/java-rust-mixed-membership.h7uJsb/opensearch/stdout.log`)를 직접 보면 `steelsearch_class_load_marker=CoordinationState=1`, `steelsearch_class_load_marker=Publication=1`, `steelsearch_publication_onResponse_entry=77`, `steelsearch_handleJoin_entry=154`가 모두 존재한다. 즉 server-side class overlay는 실제로 적용됐고, current collector가 raw OpenSearch log를 report JSON으로 승격하지 못한 것이다. 더 중요한 현재 본류 blocker는 same raw log에 `steelsearch_publication_response_class=transport_failure`와 `NodeDisconnectedException ... [internal:cluster/coordination/publish_state] disconnected`가 각각 `77건` 보인다는 점이다. 다음 남은 질문은 이 `publish_state` transport failure/disconnect가 Rust side close인지 Java transport/client path disconnect인지다.
- 2026-05-04: same-run artifact(`/tmp/java-rust-mixed-membership-class-load-marker.latest.json`) 기준 Rust `steelsearch_transport_capture`의 유일한 `publish_state` socket은 `connection_end=remote_eof`, `first_post_response_event=remote_eof`로 끝난다. same-run raw OpenSearch log에는 `NodeDisconnectedException ... [internal:cluster/coordination/publish_state] disconnected`가 `77건` 나온다. 따라서 current direction은 Rust active close보다 Java-side disconnect 쪽을 더 강하게 가리킨다. 다음 남은 질문은 Java-side `publish_state` disconnect를 실제로 유발하는 direct client-side close/connection teardown path가 무엇인지다.
- 2026-05-04: same-run server-overlay + raw-log probe(`/tmp/java-rust-mixed-membership-publish-disconnect-hints.latest.json`)에서 `steelsearch_publication_response_class=transport_failure=74`와 `NodeDisconnectedException ... [internal:cluster/coordination/publish_state] disconnected=74`는 surface되지만 `hint[explicitLocalClose]=0`이다. 따라서 current direct cause를 same-run Netty explicit-local-close path로 바로 연결할 수는 없다. 이번 회차 기준으로는 publication transport timeout/retry보다 Java-side disconnect path라는 점까지만 고정되고, 다음 남은 질문은 same-run hint layer가 비어 있는 이유가 Netty hint capture/overlay 부재인지, 아니면 disconnect가 그보다 더 상위 Java client path에서 끝나는지다.
- 2026-05-04: same-run raw log regex를 바로잡아 다시 확인하면 `steelsearch_publication_response_class=transport_failure=74`, `NodeDisconnectedException ... [internal:cluster/coordination/publish_state] disconnected=74`, `hint [explicitLocalClose]=1064`가 모두 surface되고, `transport_failure` target port `39895`가 `explicitLocalClose` remote port top bucket `39895`와 겹친다. source상 any sibling close listener는 `nodeChannels.close()` fanout을 소유하므로, current direct cause는 same-run Java client-side `explicitLocalClose` -> node connection teardown path로 보는 편이 맞다. 다음 남은 질문은 이 `explicitLocalClose`가 `publish_state` 시점에 왜 반복되는지, 즉 idle sibling stale-access close인지 publication request channel 자체 close인지다.
- 2026-05-04: same-run raw log(`/tmp/java-rust-mixed-membership-publish-disconnect-hints.latest.json`)에서 failure port `39895`의 `node connection ... channelIndex ... closeOrder`를 first-close 기준으로 다시 집계하면 `first_index_counts={0:74, 1:27, 2:9, 5:11, 6:14, 7:3, 8:4, 9:1, 10:3, 11:1, 12:1}`이고, `idle low-index first count=61`, `STATE index4 first count=0`, `PING index3 first count=0`이다. 따라서 current same-run failure port는 publication request `STATE` channel 자체 close보다 idle low-index sibling stale-access close 쪽과 더 강하게 맞는다. 다음 남은 질문은 같은 remote port `39895`에서 함께 보이는 `index0 probe family(74)`와 `idle low-index node-connection family(61)` 중 publication failure와 더 직접적으로 연결되는 family가 어느 쪽인지다.
- 2026-05-04: same-run raw log(`/tmp/java-rust-mixed-membership-publish-disconnect-hints.latest.json`)에서 `steelsearch_publication_response_class=transport_failure` `74건`을 기준으로 same-port event ordering을 다시 분류하면 직전 event는 `74/74` 모두 `named node-connection close`이고, 직후 event는 `probe_open=53`, `named_node_close=20`이다. 또한 failure 직전 latest named connection에서 이미 닫힌 채널 수는 `median=13`이며 `54/74`가 `13개` full close 뒤이고, 가장 가까운 직전 close index도 `10/11/12` tail에 몰린다. 따라서 current publication failure는 singleton `index0` probe close보다 named node-connection sibling teardown의 downstream tail에 더 직접 연결된다고 보는 편이 맞다. 남은 질문은 node-connection teardown 내부에서 publication future가 low-index stale-sibling first-close의 downstream tail을 보는 것인지, 아니면 `REG/STATE` tail-close 시점에서 최종 disconnect를 관측하는 것인지다.
- 2026-05-04: same-run raw log(`/tmp/java-rust-mixed-membership-publish-disconnect-hints.latest.json`)에서 each `steelsearch_publication_response_class=transport_failure`를 latest named node connection close sequence에 붙여 다시 비교하면 `first close -> failure` gap은 `median=40.5 lines`인데 `last close -> failure`와 `REG tail close -> failure` gap은 둘 다 `median=12 lines`다. `STATE close -> failure`도 `median=29 lines`로 더 멀다. 또한 failure 직전 closest close는 `71/74`가 `REG 7..12` family이고 non-REG는 `3건`뿐이다. 따라서 publication future는 low-index stale first-close보다 `REG/final teardown tail`에서 disconnect를 더 직접 관측한다고 보는 편이 맞다. 남은 질문은 low-index stale sibling first-close가 teardown을 시작한 뒤에도 publication-visible disconnect가 왜 `REG tail/final teardown`에서 더 늦게 surface되는지, 즉 `nodeChannels.close()` fanout ordering 문제인지 active `REG/STATE` traffic 영향인지다.
- 2026-05-04: source+same-run artifact를 같이 보면 `TcpTransport`는 any sibling close listener에서 즉시 `nodeChannels.close()`를 fanout하고, `TransportService`는 connection close 뒤 `responseHandlers.prune(... NodeDisconnectedException ...)`로 outstanding publication response를 깨운다. actual raw log에서도 `closed transport connection -> publication transport_failure` gap은 `median=11 lines`인데 `STATE close -> failure`는 `median=30 lines`, `FollowersChecker disconnected -> failure`는 `median=26 lines`, `REG tail close -> failure`는 `median=12 lines`다. 따라서 publication-visible disconnect는 active `REG/STATE` traffic 자체보다 connection-close callback chain에 더 직접 붙는다고 보는 편이 맞다. 남은 질문은 low-index stale first-close 이후 `closed transport connection`과 `NodeDisconnectedException` surface가 늦어지는 직접 원인이 `nodeChannels.close()`의 sibling fanout/수렴 ordering인지, 아니면 `TransportService`의 async `responseHandlers.prune` executor hop인지다.
- 2026-05-04: same-run raw log(`/tmp/java-rust-mixed-membership-publish-disconnect-hints.latest.json`)에서 named connection 기준 `first close -> closed transport connection -> publication transport_failure`를 다시 자르면 `first->closed` gap은 `median=25 lines`이고 `closed->failure` gap은 `median=11 lines`다(`sample_count=63`). source상 `TransportService`가 `getExecutorService().execute(...)`로 async prune hop을 갖는 것은 맞지만, current delay의 더 큰 몫은 그 이전 `nodeChannels.close()` sibling fanout/수렴 구간이라고 보는 편이 맞다. 따라서 다음 남은 질문은 timing tail보다 더 upstream으로 올라가서, low-index stale sibling `explicitLocalClose`를 실제로 발화하는 Java client-side caller/epoch가 `findPeers` singleton probe path인지, followup multichannel node-connection path인지다.
- 2026-05-04: same-run raw log(`/tmp/java-rust-mixed-membership-publish-disconnect-hints.latest.json`)에서 failure port `39895`의 named multichannel connection `74개`를 기준으로 `open -> first low-index close`와 `open -> next singleton probe open`을 비교하면 `probe_before_first_low_close=0`, `probe_after_first_low_close=73`, `no_later_probe=1`이다. `open -> first low-index close`는 `median=13 lines`인데 `open -> next probe`는 `median=107 lines`다. 따라서 low-index stale `explicitLocalClose` trigger epoch는 singleton probe가 아니라 followup multichannel node-connection path라고 보는 편이 맞다.
- 2026-05-04: same artifact에서 `74/74` 모두 `first low-index close`가 `next named reconnect open`보다 먼저 오고, 다음 named reconnect는 그 뒤 `median=114 lines` 뒤에야 열린다. 따라서 current low-index stale close는 later redundant reconnect replacement가 아니라 해당 multichannel connection self-close 쪽으로 더 좁혀진다. 남은 질문은 이제 그 self-close path 내부에서 누가 `explicitLocalClose`를 직접 호출하느냐, 즉 `NodeChannels.close()` 이전 direct channel close caller인지 keepalive/idle cleanup 계열인지다.
- 2026-05-04: source+same-run artifact를 같이 보면 `TransportKeepAlive`는 `scheduledPing.addChannel(channel)`로 등록하고 `sendPing(channel)`만 수행하며 channel close 호출이 없다. 반면 `explicitLocalClose` hint는 `Netty4TcpChannel.close()`에만 박혀 있고, same-run epoch 분리에서도 `probe_before_first_low_close=0`이다. 따라서 current low-index stale close는 keepalive/idle cleanup보다 followup multichannel self-close 내부의 direct channel close path 쪽으로 더 좁혀진다. 남은 질문은 `Netty4TcpChannel.close()`를 실제로 호출한 Java-side direct caller가 `NativeMessageHandler`/transport exception path인지, 아니면 다른 connection teardown caller인지다.
- 2026-05-04: source scan 기준 raw close call site로 남는 obvious 후보는 `NativeMessageHandler`의 handshake-incompatible `channel.close()`와 `SecureNetty4Transport` dual-mode failure `ch.close()`다. 그러나 same-run raw log(`/tmp/java-rust-mixed-membership-publish-disconnect-hints.latest.json`)에는 두 path의 고유 literal(`could not send error response to handshake...`, `dual mode handshake and OpenSearch ping has failed...`)이 모두 없다. 따라서 current `explicitLocalClose`는 이 두 exception caller보다 다른 teardown caller 쪽으로 더 좁혀진다. 남은 질문은 추측이 아니라 `Netty4TcpChannel.close()` entry에 direct caller marker나 short stack fingerprint를 실어 low-index stale close caller를 직접 surface하는 것이다.
- 2026-05-04: `Netty4TcpChannel.close()` entry에 direct caller marker를 실제로 넣고 netty4 module overlay probe(`/tmp/java-rust-mixed-membership-close-caller.latest.json`)를 재실행하면 caller marker `1045건`이 surface된다. low-index first-close connection `72개` 중 matched `64건`은 전부 단일 caller `org.opensearch.common.util.io.IOUtils#close:89`로 수렴하고 다른 caller는 보이지 않는다. 따라서 current low-index stale close direct caller는 generic `other teardown caller`보다 `IOUtils.close()` dominance로 더 좁혀진다. 남은 질문은 `IOUtils.close()` 위 한 프레임의 real business caller가 `CloseableChannel.closeChannels`, `IOUtils.closeWhileHandlingException`, 또는 다른 transport teardown path 중 무엇인지다.
- 2026-05-04: `Netty4TcpChannel.close()` caller fingerprint를 4-frame까지 확장한 actual probe(`/tmp/java-rust-mixed-membership-close-caller-great.latest.json`)에서 low-index first-close stack은 matched `64/73` 기준으로 단일 체인 `IOUtils.close:89 -> IOUtils.close:131 -> IOUtils.close:114 -> CloseableChannel.closeChannels:107`로 수렴한다. 따라서 current direct business caller는 `CloseableChannel.closeChannels`이며 `IOUtils.closeWhileHandlingException`이나 다른 candidate보다 더 직접적이다. 남은 질문은 그 위 한 단계, 즉 `CloseableChannel.closeChannels`를 low-index stale self-close epoch에서 실제로 호출한 상위 transport caller가 `TcpTransport.NodeChannels.close()`인지 다른 shutdown/teardown caller인지다.

- 2026-05-04 mixed-membership mainline update
  - latest 5-frame caller fingerprint probe(`/tmp/java-rust-mixed-membership-close-caller-5.latest.json`)에서 low-index stale self-close matched subset `68/72`는 `IOUtils.close -> IOUtils.close -> IOUtils.close -> CloseableChannel.closeChannels -> TcpTransport$NodeChannels.close` 단일 체인으로 수렴함.
  - 남은 질문은 `NodeChannels.close()` 자체가 아니라 그것을 들어오게 만든 한 단계 위 transport caller가 `ChannelsConnectedListener.closeAndFail(...)`인지, per-channel close listener callback인지, 다른 teardown path인지다.

- 2026-05-04 mixed-membership caller-chain update
  - latest 6-frame caller fingerprint probe(`/tmp/java-rust-mixed-membership-close-caller-6.latest.json`)에서 low-index stale self-close matched subset `69/73`는 `IOUtils.close -> IOUtils.close -> IOUtils.close -> CloseableChannel.closeChannels -> TcpTransport$NodeChannels.close -> TcpTransport$ChannelsConnectedListener#lambda$onResponse$0` 단일 체인으로 수렴함.
  - source line `TcpTransport.java:1123`은 `ChannelsConnectedListener.onResponse(...)` 안에서 각 sibling에 붙인 per-channel close listener가 `nodeChannels.close()`를 호출하는 자리다.
  - 남은 질문은 `NodeChannels.close()` 위 caller가 누구냐가 아니라, 그 listener를 최초로 깨운 initial sibling close event가 어느 family/index에서 시작됐고 local explicit close인지 remote close인지다.

- 2026-05-04 mixed-membership initial-close update
  - latest first-close/hint correlation (`/tmp/java-rust-mixed-membership-close-caller-6.latest.json`)에서 named connection `73건`의 initial sibling close event는 `BULK=41`, `RECOVERY=27`, `REG=5`로 low-index `BULK/RECOVERY` family가 지배적이다.
  - same-port hint는 `explicitLocalClose=70`, `closeFutureIntercepted=3`, `missing=0`이라 initial event direction도 remote close보다 local explicit close 쪽이 더 강하다.
  - 남은 질문은 initial event family가 low-index `1/2/5/6`에 치우치는 직접 원인이 channel open/access ordering인지, 별도 caller-side selection bias인지다.

- 2026-05-04 mixed-membership skew-bias update
  - first-close family skew(`BULK=41, RECOVERY=27, REG=5`)를 6th-frame caller와 다시 묶으면 `73/73` 전부 같은 `TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123` chain으로 수렴한다.
  - 따라서 current low-index starter skew는 별도 caller-side selection bias보다 공통 `NodeChannels.close()` fanout 내부 ordering/state 문제로 보는 편이 더 맞다.
  - 남은 질문은 그 ordering/state가 channel list close iteration인지, close completion race인지, lastAccessed stale-state 차이인지다.

- 2026-05-04 mixed-membership invoke-vs-observed update
  - `closeInvokeOrder` probe(`/tmp/java-rust-mixed-membership-close-invoke.latest.json`)에서 `first invoked close`와 `first observed close`를 비교하면 `same_index=41`, `different_index=33`이다.
  - invoked family는 `BULK=39, RECOVERY=27, REG=6, STATE=1, PING=1`, observed family는 `BULK=31, RECOVERY=34, REG=9`라서 surfacing skew는 simple close iteration alone보다 close callback completion race 영향을 더 크게 받는다.
  - 남은 질문은 invoke 단계 자체의 low-index skew가 static channel list ordering인지, already-closed sibling skip인지, lastAccessed stale-state와 연관된 upstream close selection인지다.

- 2026-05-04 mixed-membership invoke-ordering update
  - `closeInvokeOrder` probe(`/tmp/java-rust-mixed-membership-close-invoke.latest.json`)에서 `first invoked index == min invoked index`가 `68/74`로 성립한다.
  - source상 `TcpTransport.NodeChannels.close()`는 `CloseableChannel.closeChannels(channels, block)`를 직접 호출하므로, invoke 단계의 low-index skew는 upstream stale-state selection보다 `static channel list ordering + already-closed earlier lower-index skip`로 읽는 편이 더 맞다.
  - 남은 질문은 `first_invoked != min_invoked` 예외 6건과 rare `STATE/PING/REG` starter가 어떤 concurrent close race 또는 pre-closed state 때문에 생기는지다.

- 2026-05-04 mixed-membership invoke-exception update
  - `first_invoked != min_invoked` 예외 6건은 모두 lower-index invoke가 뒤늦게 들어오는 large order gap(`214~602`)을 보이고, one case는 duplicate index까지 있다.
  - 따라서 rare `STATE/PING/REG` starter와 invoke-stage 예외는 stable alternate ordering보다 partially pre-closed connection 위에서 repeated/concurrent fanout이 겹친 residue로 보는 편이 맞다.
  - 남은 질문은 residue 설명이 아니라, 그 repeated/concurrent fanout을 최초로 촉발한 very-first close source가 어떤 sibling family/action path인지다.

- 2026-05-04 mixed-membership very-first-trigger update
  - `closeInvokeOrder` artifact에서 same-port local invoke가 아직 없던 pre-invoke trigger candidate를 first source로 잡으면 `74건` 전부 분류되며 family는 `BULK=32`, `RECOVERY=33`, `REG=9`다.
  - 따라서 repeated/concurrent fanout을 최초로 촉발한 very-first close source는 publication action-bearing `STATE/REG/PING`보다 low-index non-action `BULK/RECOVERY` sibling family가 지배적이다.
  - 남은 질문은 이 pre-invoke low-index trigger candidate가 실제 remote-side close/channelInactive인지, 아니면 local explicit close가 늦게 surface된 residue인지다.

- 2026-05-04 mixed-membership preinvoke-direction update
  - `Netty4MessageChannelHandler` TRACE를 켠 same-run probe에서 first pre-invoke trigger `73건`은 `channelInactive_before_invoke=1`, `invoke_before_or_without_channelInactive=72`로 갈린다.
  - 따라서 current pre-invoke low-index trigger candidate는 real remote-side close보다 local explicit close가 logger/callback ordering상 늦게 surface된 residue 쪽으로 더 강하다.
  - 남은 질문은 왜 same-connection에서 `observed close`가 `close_invoked`보다 먼저 보이느냐, 즉 logger ordering/async callback interleave detail이다.

- 2026-05-04 mixed-membership residue-ordering update
  - first pre-invoke trigger의 same-port `observed close` vs later `close_invoked` timestamp를 비교하면 `async_tail=62`, `logger_interleave=11`로 async tail이 우세하다.
  - 따라서 current residue는 pure logger ordering보다 later fanout에서 already-closed channel을 다시 건드리는 delayed local close 쪽이 더 가깝다.
  - 남은 질문은 이 async tail이 repeated `NodeChannels.close()` pass의 duplicate local close인지, 다른 delayed local close path인지다.

- 2026-05-04 mixed-membership duplicate-close update
  - first pre-invoke trigger port들의 later `close_invoked` caller6는 `73/73` 전부 `TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123`다.
  - 따라서 current async tail residue는 다른 delayed local close path가 아니라 repeated `NodeChannels.close()` pass가 same channel을 duplicate local close로 다시 건드린 경우로 읽는 편이 맞다.
  - current first unresolved mainline task는 다시 success harness 재실행/real report artifact 수집이다.

- 2026-05-04 mixed-membership success-harness precondition update
  - success harness runbook는 `CLUSTER_URL/JAVA_NODE/RUST_NODE`가 전제인데 current workspace env는 모두 비어 있다.
  - repo 검색 기준 formed mixed cluster에서 이 endpoint/node metadata를 자동 handoff해 success harness를 바로 붙여주는 wrapper도 없다.
  - 따라서 current first unresolved mainline task는 harness body 실행보다 먼저 formed mixed-cluster coordinator endpoint handoff 확보다.

- 2026-05-04 mixed-membership handoff-artifact update
  - `probe_java_rust_mixed_membership.sh` report payload에 `success_harness_handoff`를 추가했고, short-timeout actual probe에서도 `cluster_url/java_node/rust_node`가 실제로 surface됨을 확인했다.
  - 따라서 current blocker는 metadata 부재가 아니라, 이 handoff를 success harness invocation에 직접 연결하는 wrapper 부재다.

- 2026-05-04 mixed-membership success-wrapper update
  - `run_java_primary_rust_replica_success_from_probe_report.sh`로 probe artifact의 `success_harness_handoff`를 직접 consume해 success harness command를 복원할 수 있게 됐다.

- 2026-05-04 mixed-membership negative-wrapper update
  - `run_java_primary_rust_replica_negative_from_probe_report.sh`를 추가해 probe artifact의 `success_harness_handoff`를 직접 consume하고 `decode_mismatch`, `apply_mismatch`, `checkpoint_mismatch` 3종 negative recipe command를 복원할 수 있게 됐다.
  - short-timeout artifact(`/tmp/java-rust-mixed-membership-handoff-fast.latest.json`)에 대한 `--print-only` smoke에서 세 fault class 모두 `cluster_url=http://127.0.0.1:33025`, `java_node=java-primary-1`, `rust_node=rust-replica-1`가 실제로 주입됨을 확인했다.
  - short-timeout artifact에 대한 actual execute에서는 `prepare` phase가 `http://127.0.0.1:33025`에 대해 `Connection refused`로 즉시 실패했다.
  - 따라서 current blocker는 wrapper 연결이 아니라 fresh/live formed mixed-cluster endpoint handoff 부재다.
  - wrapper는 이제 실행 전 `/_cluster/health` preflight로 stale handoff를 `probe handoff endpoint is not live`로 즉시 거른다.
  - `probe_java_rust_mixed_membership.sh`에 early `live_handoff_ready` report + keepalive를 추가한 뒤 fresh live handoff artifact(`/tmp/java-rust-mixed-membership-live-handoff-3.latest.json`)로 `decode_mismatch`, `apply_mismatch`, `checkpoint_mismatch` 3종을 실제 실행해 real report artifact까지는 수집했다.
  - 다만 그 handoff source 자체는 `observed_node_count=1`, `membership_formed=false`, `blocker_class=standalone_only_bootstrap`였고, collected report도 모두 `placement_observed.rust_replica=false`였다.
  - `run_java_primary_rust_replica_negative_from_probe_report.sh`는 이제 이런 one-node handoff를 `probe report is not a true 2-node mixed cluster handoff`로 즉시 거른다.
  - mixed-membership intended probe(`JAVA_RUST_MIXED_MEMBERSHIP_JAVA_WRITE_FORWARDING_VALIDATED=true`, `STEELSEARCH_SPLIT_BUILD_RUN=1`)의 fresh artifact(`/tmp/java-rust-mixed-membership-formed-source-attempt.latest.json`)는 최종적으로 `observed_node_count=0`, `membership_formed=false`, `failure_stage=membership_timeout`, `blocker_class=membership_timeout`로 닫힌다.
  - 동시에 marker는 `steelsearch_native_transport_join_participation=true`, `steelsearch_transport_follow_up_observed=true`, `steelsearch_transport_handshake_accepted=true`다.
  - raw OpenSearch stdout을 보면 `_cat/nodes` visibility failure보다 cluster-manager formation failure가 직접 원인이다. `steelsearch_handleJoin_entry`와 `elected-as-cluster-manager ([2] nodes joined)` 직후 `steelsearch_publication_response_class=transport_failure`, `FailedToCommitClusterStateException: publication failed`, `non-failed nodes do not form a quorum`가 이어진다.
  - further split 결과, current `non-failed nodes do not form a quorum`는 commit precondition mismatch보다 follower disconnect/transport teardown 쪽에 더 직접 붙는다. `FollowersChecker ... disconnected`가 먼저 나오고, 그 뒤 `rootCauseMessage=[...][internal:cluster/coordination/publish_state] disconnected`, `publication failed`, `non-failed nodes do not form a quorum` 순으로 이어지며 `commit_state` literal은 보이지 않는다.
  - Rust-side capture에서도 `publish_state` 관련 socket `1건`이 `connection_end=remote_eof`로 끝나므로, current native join disconnect는 Rust active close보다 Java-side disconnect 쪽으로 더 가깝다.
  - further split 결과, current native join failure는 publish_state response semantic rejection보다 independent transport disconnect 쪽에 더 직접 붙는다. `steelsearch_handleJoin_entry=150`인데 semantic reject marker(`term_mismatch/reboot_mismatch/better_term/better_version/missing_initial_configuration`)는 전부 `0`이고, 대신 `transport_failure=75`, `publish_state disconnected=75`, `publication failed=150`가 나온다.
  - native-caller overlay probe의 latest work dir(`/tmp/java-rust-mixed-membership.kcwQL2/opensearch/stdout.log`)에서 Rust-side publish disconnect port `58973` 관련 close caller를 집계하면 `explicitLocalClose=921`이고, caller chain은 `TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123`가 `949건`으로 지배적이다.
  - deeper native-caller stdout(`/tmp/java-rust-mixed-membership.yNJyKj/opensearch/stdout.log`)에서 Rust publish disconnect port `33333`의 first named close를 집계하면 `connection_id=2`, `peer=rust-replica-1`, `channel_index=1`, `idle_ms=800`, `close_order=2`다.
  - 따라서 current native join initial close는 anonymous handshake/probe connection close보다 named rust node connection close 쪽이 더 직접적이다.
  - further split 결과, 이 first named close는 `[2026-05-04T12:45:59,196]`이고 corresponding `steelsearch_publication_response_class=transport_failure`는 `[2026-05-04T12:45:59,232]`다. 따라서 current native join initial close는 publish_state transport callback close보다 upstream immediate transport teardown 쪽이 더 가깝다.
  - same-channel correlation까지 붙이면 Rust publish disconnect port `33333`의 first named close same-channel(`localAddress=127.0.0.1:42554`) 근처 caller line은 `[2026-05-04T12:45:59,205] ... TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123`다. timestamp는 observed close보다 `9ms` 늦지만 same-channel async tail residue로 읽는 편이 맞다.
  - 따라서 남은 질문은 current native join path에서 `ChannelsConnectedListener.onResponse -> NodeChannels.close` fanout을 먼저 깨우는 pre-fanout sibling close event가 무엇인지다.
  - further split 결과, deeper native-caller stdout(`/tmp/java-rust-mixed-membership.yNJyKj/opensearch/stdout.log`)의 first-close burst window에서 Rust publish disconnect port `33333` 기준 `closeFutureIntercepted=4`, `explicitLocalClose=0`, `close_invoked=6`이다.
  - 따라서 current native join path의 pre-fanout sibling close event는 fresh local explicit close starter보다 already-closed `closeFutureIntercepted` sibling 쪽으로 더 가깝다.
  - same-run/source further split 결과, 같은 window에서 `channelInactive=0`, `earlyChannelInactive=0`이고 source상 `Netty4Transport.addEarlyCloseFutureHintListener()`는 hint가 비어 있으면 `closeFutureIntercepted`를 직접 세운다.
  - same-run further split 결과, Rust publish disconnect port `33333`의 node connection은 opened 이후 이미 `action-tagged selected channel=6건`을 거쳤고, same-window `closeFutureIntercepted=4건`은 전부 same-port caller correlation에서 `TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123`와 다시 만난다.
  - 따라서 이 earlier Java-side closeFuture path는 connect-future failure보다 opened node-connection 위의 response-listener teardown 쪽으로 더 가깝다.
  - same-run further split 결과, Rust publish disconnect port `33333`의 first named close는 line `285`에서 시작하고, 그 직전 `steelsearch_publication_onResponse_entry`는 `discoveryNode=java-primary-1` self case `1건`뿐이다. Rust 대상 publication onResponse는 보이지 않는다.
  - `FollowersChecker disconnected/marking node as faulty`는 line `332/339`로 first close burst 뒤에 나온다.
  - further split 결과, Rust port `33333`에서 anonymous pre-node connection `[1]` observed close는 line `255`, named node connection `[2]` open은 line `271`, same named connection의 first `closeFutureIntercepted`는 line `292`다.
  - 따라서 publication response handling이나 follower-check disconnect callback보다 앞선 other connection-close callback chain의 실제 first upstream event는 anonymous pre-node connection close 쪽으로 더 가깝다.
  - fresh native-caller stdout(`/tmp/java-rust-mixed-membership.Ubhh12/opensearch/stdout.log`) 기준 anonymous pre-node connection `[1]` handshake port `33881`의 close caller line은 `[257] ... IOUtils#closeWhileHandlingException:179 -> HandshakingTransportAddressConnector$1$1$1#innerOnResponse:140`이고, corresponding observed close는 line `259`다.
  - 따라서 이 anonymous pre-node connection close direct caller/path는 seed identity handoff 직후 connect replacement teardown보다 handshake probe response completion path 쪽으로 더 가깝다.
  - same-run further split 결과, handshake probe connection `[1]`의 caller는 line `257`의 `HandshakingTransportAddressConnector$1$1$1#innerOnResponse:140`이고, observed close/closed transport connection은 `259/260`이다.
  - 이후 named node connection `[2]`는 line `275`에서 새 local port set으로 다시 열리고, later failure caller는 `290` 이후 `TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1123` 체인이다.
  - 따라서 current handshake probe response completion close는 later named node connection failure와 같은 direct caller chain이 아니라 benign한 one-shot probe teardown 쪽으로 더 가깝다.
  - same-run further split 결과, first named node connection `[2]` window의 selected index set은 `[3,4,8,9,10,11]`이고 first five close는 `channelIndex=[12,7,2,5,1]`, `closeOrder=[2,3,4,5,6]`이다.
  - 따라서 current named node connection `[2]` failure chain의 first causal event는 `publish_state` state channel, `follower_check` ping channel, selected `REG` action channel보다 non-state/non-ping unselected sibling 쪽으로 더 가깝다.
  - same-run further split 결과, first named node connection `[2]` window에서 unselected `REG` sibling(`12/7`)의 earliest closeOrder는 `2/3`이고, low-index non-action sibling(`2/5/1`)의 earliest closeOrder는 `4/5/6`이다.
  - 따라서 current named connection `[2]` failure chain의 first causal event는 low-index non-action sibling보다 unselected `REG` sibling 쪽으로 더 가깝다.
  - same-run further split 결과, first named node connection `[2]` window의 selected index set은 `[3,4,8,9,10,11]`이므로 starter `REG` indices `7/12`는 둘 다 selected action channel이 아니다.
  - 특히 local port `55142`(index `12`)는 line `314`의 `closeFutureIntercepted`가 line `333`의 `ChannelsConnectedListener#lambda$onResponse$0:1123` caller보다 먼저 온다.
  - 따라서 current unselected `REG` starter는 selected `REG` action 후속 teardown보다 unused `REG` pool stale close 또는 concurrent fanout residue 쪽으로 더 가깝다.
  - same-run further split 결과, starter `index 12` / local port `55142`는 observed close line `292`, `closeFutureIntercepted` line `314`, `ChannelsConnectedListener#lambda$onResponse$0:1123` caller line `333` 순서다.
  - 따라서 current unselected `REG` starter는 later listener fanout residue가 아니라 stale close 자체가 먼저 surface되고, 그 뒤 `NodeChannels.close` fanout이 residue로 덮는 쪽이라고 보는 편이 맞다.
  - same-run/source further split 결과, first named node connection `[2]` window의 selected index set은 `[3,4,8,9,10,11]`이고 starter `7/12`는 끝까지 selected되지 않는다.
  - source상 채널은 open 시 `markAccessed(relativeMillisTime)`를 한 번 받고, actual send 시 `OutboundHandler.sendBytes()`가 다시 `markAccessed(...)`를 호출한다.
  - starter `7/12`의 observed close idleForMs는 둘 다 `600ms`다.
  - 따라서 current unused `REG` sibling stale close는 follow-up 이후 explicit cleanup보다 never-selected idle sibling stale-access 쪽으로 더 가깝다.
  - same-run further split 결과, `REG` edge-slot orders는 `12 -> closeOrder 2`, `7 -> closeOrder 3`이고, low-index non-action은 `2 -> 4`, `5 -> 5`, `1 -> 6`이다.
  - 따라서 current `REG` starter skew는 simple static ordering alone보다 partial concurrent race가 더 직접적이다.
  - source상 `ConnectionProfile.ConnectionTypeHandle.getChannel()`은 `offset + Math.floorMod(counter.incrementAndGet(), length)` round-robin을 쓴다.
  - fresh native-caller stdout(`/tmp/java-rust-mixed-membership.Ubhh12/opensearch/stdout.log`)의 first named node connection `[2]` REG selected prefix는 실제로 `8,9,10,11`이다.
  - 따라서 current path에서 edge-slot `7/12`가 early sequence에서 비는 것은 allocator static bias와 actual selected sequence가 맞물린 결과라고 보는 편이 맞다.
  - minimal experiment로 `ConnectionProfile.ConnectionTypeHandle.getChannel()`의 REG round-robin start를 한 칸 당겼을 때(`/tmp/java-rust-mixed-membership.C3mOrw/opensearch/stdout.log`) intended named node connection `[2]` window 자체가 열리지 않았고, `cluster-manager not discovered yet` / `timed out while waiting for initial discovery state`로 Rust join 형성 전 단계에서 후퇴했다.
  - targeted early-access experiment로 `TcpTransport.NodeChannels.channel(REG)`에서 edge-slot `7/12`의 `ChannelStats.markAccessed(...)`를 함께 갱신했을 때도(`/tmp/java-rust-mixed-membership.nNro1o/opensearch/stdout.log`) intended named node connection `[2]` window 자체가 열리지 않았고, again `cluster-manager not discovered yet` 단계에서 후퇴했다.
  - 따라서 global selection-start shift와 targeted early access 모두 stale starter 해소보다 join 형성 악화 쪽으로 보인다.
  - 남은 질문은 channel-touch patch를 더 밀기보다 native Rust side join/transport path를 다시 파는 것이 맞는지, 아니면 더 보수적인 Java-side no-op access instrumentation만 가능한지다.

- baseline `/tmp/java-rust-mixed-membership.Ubhh12/opensearch/stdout.log` 대비 global selection-start shift(`/tmp/java-rust-mixed-membership.C3mOrw/opensearch/stdout.log`)와 targeted early-access(`/tmp/java-rust-mixed-membership.nNro1o/opensearch/stdout.log`)는 모두 same timeout signature(`cluster-manager not discovered yet` + `timed out while waiting for initial discovery state`)를 유지한 채 `steelsearch_handleJoin_entry`와 `steelsearch_publication_response_class=transport_failure` count를 각각 `190/94 -> 112/55 -> 60/29`로 낮췄다. 따라서 channel-touch patch line은 현 시점 mainline breaker 해소보다 join progression을 약화시키는 쪽으로 보고, 다음 우선순위는 native Rust side join/transport path에서 publication transport_failure 직전 응답/connection handling을 다시 직접 파는 쪽으로 되돌리는 것이 맞다. Java-side follow-up은 의미 변경 없는 no-op instrumentation 수준만 허용하는 편이 안전하다.

- native Rust side 본류 재확인 결과 `/tmp/java-rust-mixed-membership-formed-source-attempt.latest.json`의 `steelsearch_transport_capture`에서 `internal:cluster/coordination/publish_state`는 `response_frame_sent_at_ms - connection_started_at_ms = 17000ms`이고 응답 시점에 바로 `remote_eof`로 끝난다. 반면 `request_peers`/`pre_vote`/`follower_check`는 대체로 수십~수백 ms, `start_join`도 약 800ms 수준이다. source `crates/os-node/src/main.rs`는 `publish_state` 경로에서 `tools/parse_java_publish_state_request.sh`와 `tools/build_java_publish_with_join_response.sh` shell helper를 모두 호출한다. 따라서 current mainline blocker는 단순 Java disconnect 추상화보다 Rust `publish_state` helper path의 late response가 publication transport_failure의 직접 upstream인지 먼저 검증하는 쪽이 더 우선이다.

- fresh timing run(`/tmp/java-rust-mixed-membership.0RAhxp`)에서 `steelsearch_publish_state_decode_ms`는 `3343 -> ... -> 50582ms`, `steelsearch_publish_state_build_ms`는 `9781 -> ... -> 48132ms`, `steelsearch_publish_state_total_before_write_ms`는 `13125 -> ... -> 64898ms`로 누적 증가했다. 반면 same run OpenSearch stdout에는 `steelsearch_publication_response_class=transport_failure=73`, `failed to commit cluster state=73`가 찍힌다. 즉 current mainline blocker는 generic disconnect보다 `publish_state` shell helper path 자체의 장기 지연이 더 직접적이다. 다음 실험은 계측이 아니라 helper bypass여야 한다.

- build helper bypass experiment(`/tmp/java-rust-mixed-membership.Is7IyA`)에서 `steelsearch_publish_state_build_ms`는 전부 `0`이 됐지만, `steelsearch_publish_state_decode_ms`는 여전히 `3619 -> ... -> 42399ms`로 누적됐고 `total_before_write_ms`도 `42400ms`까지 유지됐다. same run OpenSearch stdout의 `steelsearch_publication_response_class=transport_failure`는 baseline `73`에서 오히려 `80`으로 늘었다. 따라서 `build_java_publish_with_join_response.sh` 단독 bypass는 direct fix가 아니며, current dominant helper latency는 `parse_java_publish_state_request.sh` 쪽이라고 보는 편이 맞다. experiment patch는 원복하고 다음 본류는 parse helper bypass다.

- parse helper bypass experiment(`/tmp/java-rust-mixed-membership.XdL7W0`)에서 `steelsearch_publish_state_decode_ms`는 전부 `0`이 됐고 `decode_mode=inprocess_state_fallback` marker도 찍혔다. 하지만 `steelsearch_publish_state_build_ms`는 여전히 `2763 -> ... -> 33518ms`, `total_before_write_ms`도 `33519ms`까지 남았고 same run `steelsearch_publication_response_class=transport_failure`는 `82`였다. 즉 build helper bypass와 parse helper bypass를 각각 따로 해도 publication transport_failure는 개선되지 않는다. current remaining dominant path는 shell helper 없는 in-process publish response builder 전체다. parse bypass experiment patch는 원복했다.

- full in-process publish_state experiment(`/tmp/java-rust-mixed-membership.7bNrj0`)에서는 `decode_mode=inprocess_state_fallback`가 찍힌 상태에서 `steelsearch_publish_state_decode_ms=0`, `build_ms=0`, `total_before_write_ms=0`이 전부 성립했다. 그런데 same run OpenSearch stdout의 `steelsearch_publication_response_class=transport_failure`는 여전히 `78`이고 `failed to commit cluster state`도 `150`으로 남았다. 따라서 current blocker는 shell helper latency가 아니라 in-process fallback publish response 자체의 wire/semantic mismatch다. full in-process experiment patch는 원복했다.

- semantic split 재정리: build helper bypass run(`/tmp/java-rust-mixed-membership.Is7IyA`)은 real decode를 그대로 유지하면서 fallback publish response builder만 썼는데도 `publication_transport_failure=80`이 남았다. full in-process run(`/tmp/java-rust-mixed-membership.7bNrj0`)은 decode/build latency를 사실상 0으로 만들었지만 `publication_transport_failure=78`이 남았다. 따라서 current next split은 decode latency나 synthetic decode 여부가 아니라 fallback publish response payload 자체, 특히 Join lastAccepted/source-target/target node semantics 쪽이다.

- build-bypass(`/tmp/java-rust-mixed-membership.Is7IyA`)와 full in-process(`/tmp/java-rust-mixed-membership.7bNrj0`) 둘 다 `steelsearch_handleJoin_entry`는 각각 `160/308`회 찍히지만 `term_mismatch`, `better_last_accepted_term`, `better_last_accepted_version`, `missing_initial_configuration` rejection marker와 `missing_join`은 전부 `0`이다. 따라서 current fallback publish response 문제는 Join source-target/lastAccepted가 `handleJoin`에서 곧바로 reject되는 그림보다, 그 이후 publication acceptance/quorum path에서 다른 response field가 어긋나는 그림에 더 가깝다.

- source 재확인 결과 `CoordinationState.handlePublishResponse()`는 `handleJoin` 이후 publish vote를 받아들이기 전에 `electionWon`, `publishResponse.term == currentTerm`, `publishResponse.version == lastPublishedVersion`만 검사한다. actual fallback builder runs에서는 `handleJoin_entry`가 많고 direct join rejection은 0이므로, current next split은 Join field가 아니라 top-level `PublishResponse.term/version` 또는 `electionWon` gate다.

- gate-marker run(`/tmp/java-rust-mixed-membership.owgohB/opensearch/stdout.log`)에서 `steelsearch_handlePublishResponse_gate=accepted`는 `77`회 찍히고 `election_not_won`, `term_mismatch`, `version_mismatch`는 모두 `0`이다. 그런데 same run `steelsearch_publication_response_class=transport_failure`는 `79`회 남아 있다. 따라서 current blocker는 top-level `PublishResponse.term/version` 또는 `electionWon` gate가 아니라, acceptance 이후 publication target state / transport callback chain에서 vote가 quorum까지 이어지지 못하는 later path다.

- state-marker run(`/tmp/java-rust-mixed-membership.cYtu3c/opensearch/stdout.log`)에서 `steelsearch_handlePublishResponse_gate=accepted=77`, `steelsearch_publication_target_state=waiting_for_quorum=77`, `steelsearch_publication_response_class=transport_failure=77`가 1:1로 맞물린다. `steelsearch_publication_target_state=failed`는 `154`로 더 많다. 따라서 current later path는 accepted publish response가 quorum 대기 상태에 들어간 뒤, 이후 transport callback chain에서 FAILED로 전이되는 그림이다.

- latest state-marker run(`/tmp/java-rust-mixed-membership.cYtu3c/opensearch/stdout.log`)에서는 `waiting_for_quorum`와 `accepted`가 모두 self `java-primary-1` target에만 붙는다. rust target은 `waiting_for_quorum=0`이고 `previousState=SENT_PUBLISH_REQUEST causeClass=NodeDisconnectedException`로 바로 `FAILED` 된다. 따라서 다음 분기는 self quorum tail이 아니라 rust target publish response callback이 왜 `onResponse`까지 오지 못하는지다.

- latest publication marker run(`/tmp/java-rust-mixed-membership.cYtu3c/opensearch/stdout.log`)에서는 `steelsearch_publication_onResponse_entry`가 self `java-primary-1`에는 `77`회 찍히지만 rust target에는 `0`이다. 반면 rust target `transport_failure`는 `77`회다. 따라서 current next split은 `onResponse` 이후 logic가 아니라 rust publish response가 callback entry 전에 사라지는 경로다.

- build-bypass publication-marker run(`/tmp/java-rust-mixed-membership.cYtu3c`)의 Rust stderr에는 `steelsearch_publish_state_total_before_write_ms`가 `35`회 찍혀 Rust 쪽 response build/write path가 실제로 실행된다. 그런데 Java stdout에서는 rust target `onResponse`가 `0`이고 `previousState=SENT_PUBLISH_REQUEST causeClass=NodeDisconnectedException`가 `77`회다. 따라서 current evidence는 pure Rust no-send보다 Java-side pre-onResponse disconnect 쪽으로 더 기운다. 다만 response가 Java transport pipeline에 아예 못 도달했는지, 도달 후 callback dispatch 전에 close future가 이겼는지는 아직 미분리다.

- 2026-05-05: `Transport$ResponseHandlers` marker run(`/tmp/java-rust-mixed-membership.e3HUnN/opensearch/stdout.log`)에서 rust `publish_state` handler는 `add` 후 `received` 없이 전부 `prune`된다. 다음 분리는 이 `prune`가 connection-close callback chain인지 timeout cleanup인지다.

- 2026-05-05: `TransportService` source상 timeout cleanup은 `responseHandlers.remove(requestId)`를 쓰고, `onConnectionClosed(...)`만 `responseHandlers.prune(...)`를 쓴다. same-run raw log(`/tmp/java-rust-mixed-membership.e3HUnN/opensearch/stdout.log`)에서는 rust `publish_state` prune 72건 전부 직전에 `FollowersChecker ... disconnected`가 있으며 timeout warning은 0이다. 따라서 current prune path는 timeout이 아니라 connection-close callback chain이다.

- 2026-05-05: close-direction run(`/tmp/java-rust-mixed-membership.RnMQU0/opensearch/stdout.log`)에서 rust target port `52561`는 first `FollowersChecker ... disconnected` 이전에 same-port `explicitLocalClose=35`, `closeFutureIntercepted=1`, `channelInactive=0`으로 집계된다. 따라서 current rust publish_state prune의 upstream close는 remote close first보다 Java client-side teardown 쪽이다.

- 2026-05-05: same-run caller window(`/tmp/java-rust-mixed-membership.RnMQU0/opensearch/stdout.log`)에서 rust `publish_state` add(line 290) 이후 first disconnect(line 353) 전 same-port close caller는 `TcpTransport$NodeChannels#close:355` 13건, 그 상위는 `TcpTransport$ChannelsConnectedListener#lambda$onResponse$0:1132` 13건으로 수렴한다. current publish_state teardown direct caller는 `closeAndFail/onFailure`가 아니라 publication-era `lambda$onResponse$0 -> NodeChannels.close` 체인이다.


2026-05-05 publish_state fanout starter origin update

- same-run `/tmp/java-rust-mixed-membership.RnMQU0/opensearch/stdout.log`에서 `publish_state add` 이후 first `closeFutureIntercepted` starters는 anonymous/probe residue가 아니라 `opened transport connection [2]` 채널 목록의 `localAddress 43372/43308` (`channelIndex 12/1`)로 확인됨
- 의미:
  - 현재 분기는 pre-node probe 잔재보다 same named node-connection 내부 unused sibling stale close 쪽으로 더 좁혀짐
  - 다음 질문은 이 stale close가 `never-selected/never-accessed` 때문인지, same connection 내부 close-future race 때문인지임


2026-05-05 same named starter stale-access update

- same-run `/tmp/java-rust-mixed-membership.RnMQU0/opensearch/stdout.log`에서 connection `[2]`의 first disconnect 전 selected indices는 `3/4/7/8/9/10`뿐이며 starter `12/1`은 selected되지 않음
- starter `12/1`의 `idleForMs`가 둘 다 `800ms`이고 `closed transport connection [2] with age [800ms]`와 일치함
- 의미:
  - current evidence는 same connection 내부 close-future race보다 `never-access stale close` 쪽이 더 강함
  - 남은 질문은 이 unselected sibling이 왜 `explicitLocalClose`가 아니라 `closeFutureIntercepted`로 surface되는지임


2026-05-05 closeFutureIntercepted surfacing update

- source상 `Netty4Transport.addEarlyCloseFutureHintListener()`는 close future가 먼저 끝나면 hint를 `closeFutureIntercepted`로 세움
- source상 `OutboundHandler` send path는 `markAccessed(...)`를 호출함
- same-run `/tmp/java-rust-mixed-membership.RnMQU0/opensearch/stdout.log`에서 starter `12/1`은 first disconnect 전 selected set 밖에 있고, `closeFutureIntercepted` hint가 local close invoke보다 먼저 찍힘
- 의미:
  - 현재 evidence는 `explicitLocalClose` starter보다 `unused sibling + peer/closeFuture first` 쪽이 더 강함
  - 남은 질문은 peer가 왜 이 never-access sibling을 먼저 닫는지, Rust non-response/idle FIN인지 Java-side unused-channel cleanup 성격인지임


2026-05-05 peer-side first close update

- source상 `ClusterConnectionManager.closeInternal()`은 전체 node connection close이며, per-unused-sibling idle cleanup symbol은 보이지 않음
- same-run `/tmp/java-rust-mixed-membership.RnMQU0/opensearch/stdout.log`에서 starter `12/1`은 unselected 상태이고 `closeFutureIntercepted`가 local close invoke보다 먼저 옴
- 의미:
  - current evidence는 Java unused-channel cleanup보다 peer-side first close 쪽으로 더 기운다
  - 남은 질문은 Rust가 request 미수신 idle socket을 먼저 FIN하는지, 아니면 helper-latency 동안 다른 lifecycle path가 끊는지임


2026-05-05 Rust pre-first-frame ending update

- fresh `/tmp/java-rust-mixed-membership.MCpOtc/steelsearch/data/transport-seed-capture.json`에는 pre-first-frame capture가 `182`건 있고, ending은 `idle_timeout=181`, `remote_eof=1`
- 의미:
  - Rust가 never-access sibling을 proactive FIN으로 먼저 닫는 증거보다, first frame을 못 받은 채 `750ms` read timeout으로 수거되는 idle lifecycle 쪽이 훨씬 강함
  - 남은 질문은 이 `750ms` timeout 자체가 direct cause인지, Java helper-latency/unused sibling churn이 upstream에서 timeout을 밟게 하는지임


2026-05-05 5s pre-first-frame timeout experiment update

- env `STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS=5000`로 fresh probe(`/tmp/java-rust-mixed-membership.QxL2L7`)를 돌리자 Rust pre-first-frame capture가 baseline `idle_timeout=181`에서 `remote_eof=5, idle_timeout=0` 수준으로 바뀜
- same run report는 `membership_formed=true`, `observed_node_count=2`, `failure_stage=none`, `blocker_class=None`
- 의미:
  - current direct blocker는 helper-latency 단독이 아니라 Rust `750ms` pre-first-frame timeout이 실제 mixed-membership formation을 무너뜨리는 쪽으로 충분히 강함
  - 다음 질문은 이 5s setting이 stable fix인지, 그리고 이 formed cluster를 이용해 pending negative path artifacts를 재수집할 수 있는지임


2026-05-05 formed handoff negative rerun artifact layout update

- formed handoff `/tmp/java-rust-mixed-membership-live-5s.handoff.json`는 실제로 `membership_formed=true`, `observed_node_count=2`, `cluster_url=http://127.0.0.1:49475`를 담고 있고, 이를 사용한 negative wrapper actual run 3종도 모두 harness completion까지는 정상 종료됨
- 하지만 wrapper 기본 `REPORT_DIR=/home/ubuntu/steelsearch/target/java-primary-rust-negative`가 fault별로 분리되지 않아, 2026-05-05 fresh actual 산출물은 공용 `target/java-primary-rust-negative/java-primary-rust-replica/report.json` 하나에 마지막 run(`checkpoint_mismatch`)만 남는다
- 기존 fault별 경로:
  - `/home/ubuntu/steelsearch/target/java-primary-rust-negative-decode_mismatch/java-primary-rust-replica/report.json`
  - `/home/ubuntu/steelsearch/target/java-primary-rust-negative-apply_mismatch/java-primary-rust-replica/report.json`
  - `/home/ubuntu/steelsearch/target/java-primary-rust-negative-checkpoint_mismatch/java-primary-rust-replica/report.json`
  는 수정시각이 모두 `2026-05-04 12:27 UTC`인 stale artifact다
- 따라서 다음 직접 작업은 wrapper가 fault별 `report-dir`을 사용하도록 바꿔 formed 2-node handoff 기준 fresh negative artifact 3종을 각각 보존하게 만드는 것이다


2026-05-05 formed handoff negative rerun artifact layout resolved

- wrapper 기본 `REPORT_DIR`를 fault별 `target/java-primary-rust-negative-${FAULT_CLASS}`로 분리한 뒤 formed handoff `/tmp/java-rust-mixed-membership-live-5s-rerun5.handoff.json` (`membership_formed=true`, `observed_node_count=2`, `cluster_url=http://127.0.0.1:59909`)로 `decode_mismatch`, `apply_mismatch`, `checkpoint_mismatch`를 실제 재실행함
- fresh fault별 report 3개가 모두 2026-05-05 02:18 UTC에 다시 써졌고 divergence도 각각 기대값과 일치함:
  - `decode_mismatch -> divergence_classification=decode_mismatch`
  - `apply_mismatch -> divergence_classification=apply_mismatch`
  - `checkpoint_mismatch -> divergence_classification=checkpoint_mismatch`
- 현재 남은 질문은 artifact 보존이 아니라, `STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS=5000`을 임시 env 우회로 둘지, probe/harness 기본값 또는 정식 transport policy로 승격할지다


2026-05-05 success path actual artifact collection update

- formed handoff `/tmp/java-rust-mixed-membership-live-5s-success2.handoff.json`는 `membership_formed=true`, `observed_node_count=2`, `cluster_url=http://127.0.0.1:48429`를 담고 있고, success wrapper를 actual로 다시 실행해 fresh report `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/report.json`를 실제 생성함
- success wrapper는 `check || test $? -eq 2`로 조정해 divergence가 있어도 final report가 남도록 바뀜
- fresh success report는
  - `artifact_source=actual-phase-artifacts`
  - `phase_artifacts={prepare,write,read,check}`
  - `placement_observed={"java_primary": true, "rust_replica": false}`
  - `observed_failure_classes=["checkpoint_mismatch"]`
  - `divergence_classification="checkpoint_mismatch"`
  를 담음
- existing checker `check-java-primary-rust-replica-actual-run-report.py`는 아직 `phase_artifacts must cover all required phases`로 실패하는데, 이는 success wrapper가 actual `recover/restart` artifact를 아직 남기지 않기 때문임
- 따라서 current next gap은 success path artifact 부재가 아니라, reusable connected path 및 actual recover/restart phase artifact 부재 속에서 success report가 여전히 `checkpoint_mismatch`로 남는 점이다


2026-05-05 default 5s runtime follow-up promotion update

- `crates/os-node/src/main.rs`의 Rust transport pre-first-frame timeout default를 `750ms`에서 `5000ms`로 올린 뒤 env override 없이 fresh actual probe `/tmp/java-rust-mixed-membership-default5s.latest.json`를 다시 실행함
- 결과:
  - `membership_formed=true`
  - `observed_node_count=2`
  - `failure_stage=none`
  - `blocker_class=None`
  - transport capture action counts:
    - `internal:cluster/request_pre_vote = 2`
    - `internal:cluster/coordination/start_join = 2`
    - `internal:cluster/coordination/publish_state = 1`
- OpenSearch stdout에는 residual `steelsearch_publication_response_class=transport_failure=1`이 남지만, cluster formation blocker는 해소됨
- 따라서 current direct blocker는 더 이상 one-shot `remote_eof` reusable-promotion failure가 아니라, formed success path에서 Rust replica placement가 아직 `false`로 남는 recovery/restart/checkpoint side gap이다


2026-05-05 recovery/restart metadata wiring update

- `probe_java_rust_mixed_membership.sh`는 이제 formed work_dir에 다음 actual restart-control metadata를 남김:
  - `opensearch/pid`
  - `opensearch/start-command.txt`
  - `steelsearch/pid`
  - `steelsearch/start-command.txt`
- fresh probe `/tmp/java-rust-mixed-membership-restart-metadata.latest.json`에서:
  - `membership_formed=true`
  - `observed_node_count=2`
  - `failure_stage=none`
  - `blocker_class=None`
  - artifact paths:
    - `/tmp/java-rust-mixed-membership.o89KcT/opensearch/pid`
    - `/tmp/java-rust-mixed-membership.o89KcT/opensearch/start-command.txt`
    - `/tmp/java-rust-mixed-membership.o89KcT/steelsearch/pid`
    - `/tmp/java-rust-mixed-membership.o89KcT/steelsearch/start-command.txt`
- 따라서 다음 직접 작업은 recover/restart compare 자체를 추상적으로 다시 찾는 것이 아니라, 이 pid/start-command metadata를 실제 `recover-cmd` / `restart-cmd` wiring에 연결해 post-restart readback artifact를 남기는 것이다


2026-05-05 actual recover/restart compare update

- formed handoff `/tmp/java-rust-mixed-membership-live-5s-success3.handoff.json`를 사용한 success harness actual rerun에서 `recover`/`restart` phase까지 실제 수행됨
- fresh artifact:
  - `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/phase-artifacts/recover.json`
  - `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/phase-artifacts/restart.json`
  - `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state/recover-state.json`
  - `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state/restart-read-search.json`
- fresh success report는 이제 `phase_artifacts={prepare,write,read,recover,restart,check}`를 모두 포함하고:
  - `recovery_outcome=rust-restart-completed`
  - `recovered_node_count=1`
  - `post_restart_read_total_hits=3`
  를 담음
- checker `check-java-primary-rust-replica-actual-run-report.py`는 이제 phase coverage가 아니라 `divergence_classification must be none for success path`에서 실패함
- 즉 current remaining blocker는 recover/restart artifact 부재가 아니라, actual restart 뒤에도 `placement_observed.rust_replica=false`와 `checkpoint_mismatch`가 남는 success compare divergence 자체다


2026-05-05 allocation explain update for success/restart report

- fresh actual artifact `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state/check-allocation-explain.json`를 추가 수집함
- 내용:
  - `current_state=unassigned`
  - `can_allocate=no`
  - `allocate_explanation='cannot allocate because allocation is not permitted to any of the nodes'`
  - `unassigned_info.reason=INDEX_CREATED`
  - `node_allocation_decisions`에는 `java-primary-1`만 있고, 그 이유는 `same_shard=NO`
- 중요한 점:
  - explain에 Rust node가 candidate로 아예 나타나지 않음
  - 따라서 current direct cause는 Rust replica의 recovery lag나 post-restart timing보다, Rust node가 allocation candidate set에 들어오지 못하는 cluster node visibility / role / attribute gap 쪽임


2026-05-05 cluster HTTP node visibility update

- fresh actual artifact:
  - `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state/check-nodes.json`
  - `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state/check-cat-nodes.json`
- 결과:
  - `_nodes.total=1`
  - `cluster_http_node_names=["java-primary-1"]`
  - `_cat/nodes`에도 `java-primary-1`만 존재
  - report summary는 `rust_node_http_visible=false`, `rust_node_http_roles=null`
- 따라서 current direct cause는 allocation decider 세부 조건보다 앞단이다:
  - transport/membership probe는 `membership_formed=true`, `observed_node_count=2`를 보여주지만
  - OpenSearch HTTP cluster node roster는 Rust node를 전혀 싣지 않는다
- 다음 직접 질문은 `why formed mixed membership does not register Rust node into OpenSearch HTTP cluster-state node roster`다


2026-05-05 cluster-state node registration update

- fresh actual artifact:
  - `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state/check-cluster-state-nodes.json`
  - `/home/ubuntu/steelsearch/target/java-mixed-cluster-binary/java-primary-rust-replica/report.json`
- 결과:
  - `cluster_state_node_names=["java-primary-1"]`
  - `rust_node_in_cluster_state=false`
  - report summary도 `cluster_http_node_names=["java-primary-1"]`, `rust_node_http_visible=false`와 동일 방향
- 따라서 current gap은 단순 HTTP `_nodes` presentation 문제가 아니다:
  - formed transport/membership는 관측되지만
  - Rust node는 OpenSearch cluster-state node roster에 아예 등록되지 않는다
- 다음 직접 질문은 `why formed mixed membership does not progress into OpenSearch join publication / cluster-state node registration for rust-replica-1`다


2026-05-05 join publication vs persistent cluster-state registration update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_join_publication_registration_gap_after_brief_apply.py`
  - target log: `/tmp/java-rust-mixed-membership.aIbMEE/opensearch/stdout.log`
- 결과:
  - `rust_join=3`
  - `rust_publish_accepted=3`
  - `cluster_applier_added_rust=1`
  - `rust_transport_failure=1`
  - `quorum_failure=4`
  - `java_only_reelection=3`
- 의미:
  - Rust는 join/publication에 전혀 못 들어가는 것이 아니다
  - 적어도 한 번은 `ClusterApplierService ... added {{rust-replica-1}}`까지 도달한다
  - 하지만 곧바로 Rust target `publish_state` disconnect와 quorum failure가 뒤따르고, 이후 `previous [], current [{java-primary-1}]` 형태의 java-only re-election이 반복된다
- 따라서 current direct cause는 `no registration ever`가 아니라:
  - Rust registration이 brief apply 뒤 지속되지 못하고
  - repeated publish disconnect / quorum failure 때문에 final cluster-state roster에서 다시 탈락하는 것
- 다음 직접 질문은 `why rust target publish acceptance is followed by NodeDisconnectedException/quorum failure instead of persistent cluster-state membership`다


2026-05-05 followers-checker removal after rust publish acceptance update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_rust_publish_acceptance_is_followed_by_followerschecker_removal.py`
  - target log: `/tmp/java-rust-mixed-membership.aIbMEE/opensearch/stdout.log`
- 결과:
  - `rust_accept=3`
  - `follower_disconnected=3`
  - `follower_faulty=3`
  - `node_left=1`
  - `transport_failure=1`
  - `accepted_then_disconnect=3`
- 의미:
  - Rust `publish_state` acceptance 자체는 통과한다
  - 그러나 그 직후 later path는 join reject가 아니라 `FollowersChecker disconnected -> marking node as faulty -> node-left removal` chain이다
  - 즉 final roster gap은 publish payload gate보다 뒤, follower-check transport path에서 Rust node가 끊긴 것으로 보이는 문제에 더 가깝다
- 다음 직접 질문은 `why rust-replica-1 looks disconnected/faulty to FollowersChecker immediately after publish acceptance`다


2026-05-05 follower-check transport lifecycle update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_followerschecker_disconnect_matches_remote_eof_after_response.py`
  - transport capture: `/tmp/java-rust-mixed-membership.aIbMEE/steelsearch/data/transport-seed-capture.json`
  - stdout: `/tmp/java-rust-mixed-membership.aIbMEE/opensearch/stdout.log`
- 결과:
  - `rust_follower_check_count=3`
  - `rust_follower_response_then_remote_eof=3`
  - `java_follower_disconnected=3`
  - `java_follower_faulty=3`
  - `java_transport_failure=1`
- 의미:
  - current issue는 follower-check `미응답`이 아니다
  - Rust는 follower_check에 실제로 응답하지만, 그 connection이 매번 `response 후 즉시 remote_eof`로 끝난다
  - Java는 바로 그 lifecycle을 `FollowersChecker disconnected`로 받아 faulty/node-left로 이어간다
- 따라서 다음 직접 질문은 `why follower_check is still on a one-shot response-then-remote_eof lifecycle instead of the reusable connected path`다


2026-05-05 follower-check runtime hold-open policy split update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_follower_check_runtime_still_uses_one_shot_hold_open.py`
  - transport capture: `/tmp/java-rust-mixed-membership.aIbMEE/steelsearch/data/transport-seed-capture.json`
  - source: `/home/ubuntu/steelsearch/crates/os-node/src/main.rs`
- 결과:
  - `follower_check_count=3`
  - `follower_check_remote_eof=3`
  - `follower_check_proactive_keepalive=0`
  - `source_follower_check_hold_open_false=True`
  - `source_publish_state_hold_open_true=True`
  - `source_start_join_hold_open_true=True`
- 의미:
  - current follower-check disconnect는 단순 peer randomness가 아니다
  - runtime source상 follower_check branch만 still one-shot `hold_transport_channel_open(..., false, ...)` policy를 사용한다
  - publish_state / start_join은 이미 reusable connected path 쪽(`true`)으로 올라가 있다
- 따라서 다음 직접 질문은 분석보다 구현 쪽이다:
  - `if follower_check is promoted to the same reusable connected path, does persistent cluster-state membership and rust HTTP visibility recover?`


2026-05-05 follower-check direct promotion experiment update

- experiment patch:
  - `/home/ubuntu/steelsearch/crates/os-node/src/main.rs`
  - follower_check branch를 `hold_transport_channel_open(..., true, ...)`로 변경
- actual run:
  - expected handoff: `/tmp/java-rust-mixed-membership-live-followercheck-keepalive.handoff.json`
  - actual latest workdir: `/tmp/java-rust-mixed-membership.T7dj4V`
- 결과:
  - handoff file가 생성되지 않음
  - latest stdout에는 `elected-as-cluster-manager ([1] nodes joined)`만 보이고 Rust join/registration 흔적이 없음
  - 즉 simple boolean flip alone은 cluster-state persistence 회복으로 이어지지 않았고, 오히려 formed mixed-cluster 이전 단계로 후퇴했다
- 따라서 다음 직접 질문은 `which extra condition is missing for follower_check reusable path (pre-bootstrap gating, keepalive cadence, or ordering split), since a bare hold-open flip regresses to one-node bootstrap`다


2026-05-05 follower-check flip regression timing update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_follower_check_flip_regression_happens_before_any_follower_check.py`
  - transport capture: `/tmp/java-rust-mixed-membership.T7dj4V/steelsearch/data/transport-seed-capture.json`
  - stdout: `/tmp/java-rust-mixed-membership.T7dj4V/opensearch/stdout.log`
- 결과:
  - `follower_check_count=0`
  - `publish_state_self_only=2`
  - `publish_state_rust=0`
  - `one_node_election=1`
- 의미:
  - current regression run에서는 follower_check actual traffic 자체가 한 번도 시작되지 않았다
  - 따라서 bare hold-open flip regression은 follower_check steady-state keepalive/cadence 문제보다 더 앞, pre-bootstrap discovery/join 단계에서 발생했다
- 다음 직접 질문은 `is the regression deterministic evidence that follower_check needs explicit pre-bootstrap gating, or just run-to-run discovery nondeterminism?`다


2026-05-05 patched follower-check A/B rerun update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_follower_check_flip_ab_points_to_discovery_nondeterminism.py`
  - run A:
    - `/tmp/java-rust-mixed-membership.oG1I9L/steelsearch/data/transport-seed-capture.json`
    - `/tmp/java-rust-mixed-membership.oG1I9L/opensearch/stdout.log`
  - run B:
    - `/tmp/java-rust-mixed-membership.T7dj4V/steelsearch/data/transport-seed-capture.json`
    - `/tmp/java-rust-mixed-membership.T7dj4V/opensearch/stdout.log`
- 결과:
  - run A:
    - `follower_check_count=3`
    - `publish_state_count=3`
    - `rust_publish_accepted=3`
    - `node_left=3`
  - run B:
    - `follower_check_count=0`
    - `publish_state_count=0`
    - `rust_publish_accepted=0`
    - `one_node_election=1`
- 의미:
  - same patched runtime에서도 한 run은 Rust traffic/follower_check까지 진행되고, 다른 run은 그 이전 one-node bootstrap에서 멈춘다
  - 따라서 bare global follower_check hold-open flip의 current regression signature는 single deterministic pre-bootstrap gate보다 run-to-run discovery nondeterminism이 더 크다
- 다음 직접 질문은 `how to gate follower_check reusable path explicitly post-bootstrap/post-rust-join instead of flipping it globally`다


2026-05-05 version-only gate insufficiency update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_version_only_gate_would_enable_too_early.py`
  - source: `/home/ubuntu/steelsearch/crates/os-node/src/main.rs`
  - self-only stdout: `/tmp/java-rust-mixed-membership.T7dj4V/opensearch/stdout.log`
- 결과:
  - `state_has_only_term_version=True`
  - `self_accepts=2`
  - `rust_accepts=0`
  - `one_node_election=1`
- 의미:
  - current runtime state에는 `last_accepted_term/version`밖에 없고 peer-aware flag가 없다
  - 그런데 self-only bootstrap run에서도 self publish acceptance가 이미 2회 일어난다
  - 따라서 `last_accepted_version > 0` 같은 generic version-only gate는 follower_check reusable path를 너무 이르게 켠다
- 다음 직접 질문은 `which peer-aware flag (e.g. non_self_publish_seen or rust_join_seen) should gate follower_check reusable path post-rust-join`이다


2026-05-05 peer-aware gate patch validation update

- experiment patch:
  - `/home/ubuntu/steelsearch/crates/os-node/src/main.rs`
  - `DevTransportCoordinationState.non_self_publish_seen` 추가
  - follower_check reusable path는 이 flag 이후에만 활성화
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_peer_aware_gate_patch_still_self_bootstraps.py`
  - target runs:
    - `/tmp/java-rust-mixed-membership.pWRUnA/opensearch/stdout.log`
    - `/tmp/java-rust-mixed-membership.MWpKf3/opensearch/stdout.log`
- 결과:
  - 두 run 모두 `one_node_election=1`
  - 두 run 모두 `rust_accept=0`
  - 두 run 모두 `self_accept=2`
- 의미:
  - peer-aware gate patch도 cluster formation을 Rust join까지 끌고 가지 못했다
  - current regression point는 follower_check reusable activation 이후가 아니라, 그보다 앞선 Rust discovery/join bootstrap 단계로 다시 올라간다
- 다음 직접 질문은 `why the peer-aware gate patch still loses Rust discovery/join before any rust-side publish acceptance appears`다


2026-05-05 peer-aware patch dead-code-in-regression update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_peer_aware_patch_paths_never_execute_in_self_bootstrap_runs.py`
  - source: `/home/ubuntu/steelsearch/crates/os-node/src/main.rs`
  - captures:
    - `/tmp/java-rust-mixed-membership.pWRUnA/steelsearch/data/transport-seed-capture.json`
    - `/tmp/java-rust-mixed-membership.MWpKf3/steelsearch/data/transport-seed-capture.json`
- 결과:
  - `patch_is_limited_to_publish_and_follower=True`
  - run A: `publish_state=0`, `follower_check=0`, `tcp_handshake=1`
  - run B: `publish_state=0`, `follower_check=0`, `tcp_handshake=1`
- 의미:
  - self-only regression runs에서는 새 peer-aware patch branch가 실제로 한 번도 실행되지 않았다
  - 따라서 current regression을 patch branch semantics로 설명하는 것은 맞지 않고, upstream discovery path nondeterminism 쪽으로 다시 올라가야 한다
- 다음 직접 질문은 `where the pre-bootstrap discovery path stops after tcp_handshake and before request_peers/transport_handshake/join`이다


2026-05-05 discovery stop-point after tcp handshake update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_discovery_regression_stops_after_tcp_handshake.py`
  - source: `/home/ubuntu/steelsearch/crates/os-node/src/main.rs`
  - captures:
    - `/tmp/java-rust-mixed-membership.pWRUnA/steelsearch/data/transport-seed-capture.json`
    - `/tmp/java-rust-mixed-membership.MWpKf3/steelsearch/data/transport-seed-capture.json`
- 결과:
  - `source_has_follow_ups=True`
  - both runs:
    - `tcp=1`
    - `transport=0`
    - `request_peers=0`
    - `tcp_no_follow_up=1`
- 의미:
  - Rust runtime은 `transport_handshake` / `request_peers` follow-up을 받을 준비가 있다
  - 그러나 current regression runs에서는 Java가 `tcp_handshake` 응답을 받은 뒤 follow-up을 전혀 보내지 않고 즉시 `remote_eof`로 끝낸다
- 다음 직접 질문은 `does Java reject the tcp handshake identity payload itself, or does the connector receive it and still choose a replacement/close path before sending transport_handshake/request_peers?`다


2026-05-05 handshake-payload-mismatch split update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_discovery_stop_points_away_from_handshake_payload_mismatch.py`
  - source: `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/HandshakingTransportAddressConnector.java`
  - captures/stdout:
    - `/tmp/java-rust-mixed-membership.pWRUnA/...`
    - `/tmp/java-rust-mixed-membership.MWpKf3/...`
- 결과:
  - `source_warns_on_high_level_failure=True`
  - both runs:
    - `transport_handshake=0`
    - `handshake_failed_warn=0`
- 의미:
  - current regression runs는 logged high-level handshake payload mismatch와는 잘 맞지 않는다
  - stop point는 `transport_handshake` request가 나가기 전, 즉 low-level `tcp_handshake` 응답 직후 connector-side follow-up close/replacement path에 더 가깝다
- 다음 직접 질문은 `why HandshakingTransportAddressConnector closes/replaces the probe path before sending transportService.handshake()/request_peers follow-up in these regression runs`다


2026-05-05 probe-connector entry marker update

- instrumentation:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/HandshakingTransportAddressConnector.java`
  - `steelsearch_probe_stage=*` warn marker 추가
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_discovery_regression_never_enters_probe_connector.py`
  - stdout: `/tmp/java-rust-mixed-membership.1GiGgc/opensearch/stdout.log`
- 결과:
  - `source_has_probe_markers=True`
  - `marker_count=0`
  - `one_node_election=1`
- 의미:
  - current regression run은 `HandshakingTransportAddressConnector` 내부 close/replacement path까지도 들어가지 않는다
  - 즉 blocker는 connector 내부 follow-up split보다 앞, `PeerFinder/seed-host discovery -> connector invocation` 이전 단계다
- 다음 직접 질문은 `why PeerFinder/seed-host discovery never reaches HandshakingTransportAddressConnector invocation in the self-only regression runs`다


2026-05-05 peerfinder marker boundary update

- instrumentation:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
  - `steelsearch_peerfinder_stage=*` warn marker 추가
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_peerfinder_reaches_establish_connection_but_not_connector_callback.py`
  - stdout: `/tmp/java-rust-mixed-membership.F2aUvL/opensearch/stdout.log`
- 결과:
  - `resolved_configured_hosts=1`
  - `start_probe=2`
  - `establish_connection=1`
  - `connection_response=0`
  - `connection_failure=0`
  - `probe_marker=0`
- 의미:
  - current regression run은 seed host resolve와 `PeerFinder.establishConnection()`까지는 실제로 도달한다
  - 그러나 그 다음 `transportAddressConnector.connectToRemoteMasterNode()` callback도, connector probe entry도 전혀 관측되지 않는다
  - 따라서 current stop point는 `PeerFinder.establishConnection()` 이후 `connectToRemoteMasterNode()/openConnection listener scheduling` 경계다
- 다음 직접 질문은 `why connectToRemoteMasterNode callback never opens in the self-only regression run even though establishConnection is reached`다


2026-05-05 open-connection marker boundary update

- instrumentation:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/HandshakingTransportAddressConnector.java`
  - `steelsearch_open_connection_stage=request/response/failure` marker 추가
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_peerfinder_establish_stops_before_connector_body.py`
  - stdout: `/tmp/java-rust-mixed-membership.t97Mb1/opensearch/stdout.log`
- 결과:
  - `resolved_configured_hosts=1`
  - `establish_connection=1`
  - `open_connection_request=0`
  - `probe_stage=0`
  - `one_node_election=1`
- 의미:
  - current regression run은 `PeerFinder.establishConnection()`까지는 실제로 도달한다
  - 그러나 connector body first-line marker인 `steelsearch_open_connection_stage=request`조차 전혀 찍히지 않는다
  - 따라서 current stop point는 `openConnection callback/listener scheduling`이 아니라 `PeerFinder -> transportAddressConnector.connectToRemoteMasterNode(...)` invocation/body-entry 경계다
- 다음 직접 질문은 `why the regression run never enters HandshakingTransportAddressConnector.connectToRemoteMasterNode(...) body even though PeerFinder.establishConnection() is reached`다


2026-05-05 connector invoke-boundary update

- instrumentation:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java`
  - `steelsearch_peerfinder_stage=before_connector_invoke/after_connector_invoke/connector_invoke_threw` marker 추가
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_peerfinder_invoke_reaches_connector_dispatch_boundary.py`
- fresh artifact:
  - `/tmp/java-rust-mixed-membership.Ku3vUJ/opensearch/stdout.log`
- 결과:
  - `establish_connection=37`
  - `before_connector_invoke=37`
  - `after_connector_invoke=37`
  - `connector_invoke_threw=0`
  - `open_connection_request=0`
  - `probe_stage=0`
- 의미:
  - 이 split은 `PeerFinder` call-site에서 invoke 자체가 안 되는지와, invoke는 되지만 `HandshakingTransportAddressConnector` 내부 `threadPool.generic().execute(...)` dispatch/body-entry가 안 열리는지를 분리하기 위한 것이다
- 결론:
  - current regression run에서는 `PeerFinder`가 connector를 실제로 invoke하고 정상 return까지 한다
  - 그러나 connector body first-line marker가 여전히 0이므로, blocker는 `PeerFinder` 이전이 아니라 connector 내부 generic execute dispatch/body-entry 쪽이다
- 다음 직접 질문은 `why connector generic-execute dispatch/body-entry never starts even though PeerFinder invokes connectToRemoteMasterNode() and returns normally`다


2026-05-05 connector generic-execute stage update

- instrumentation:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/HandshakingTransportAddressConnector.java`
  - `steelsearch_connector_stage=method_entry/before_generic_execute/after_generic_execute/task_body_entry/task_rejection/task_failure` marker 추가
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_connector_generic_execute_stops_before_task_body.py`
- fresh artifact:
  - `/tmp/java-rust-mixed-membership.3aSgG8/opensearch/stdout.log`
- 결과:
  - `method_entry=37`
  - `before_generic_execute=37`
  - `after_generic_execute=37`
  - `task_body_entry=0`
  - `task_rejection=0`
  - `task_failure=0`
  - `open_connection_request=0`
- 의미:
  - 이 split은 connector method body에는 진입하는지, generic execute submit은 정상 return하는지, 그리고 submitted task body가 실제 실행되는지를 분리하기 위한 것이다
- 결론:
  - current regression run에서는 connector method body와 generic execute submit/return까지는 실제로 진행된다
  - 그러나 submitted task body는 한 번도 시작되지 않으므로, blocker는 `PeerFinder`나 connector submit 이전이 아니라 generic executor가 task를 실제 실행하지 않는 경계다
- 다음 직접 질문은 `why the submitted connector task never starts its body after generic().execute(...) returns normally`다


2026-05-05 connector sentinel split update

- instrumentation:
  - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/HandshakingTransportAddressConnector.java`
  - connector submit 직후 same generic executor에 no-op sentinel 추가
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_connector_task_suppression_vs_dead_executor.py`
  - stdout: `/tmp/java-rust-mixed-membership.UwgS0S/opensearch/stdout.log`
- 결과:
  - `after_generic_execute=37`
  - `post_submit_sentinel_ran=37`
  - `task_body_entry=0`
  - `task_rejection=0`
  - `task_failure=0`
- 의미:
  - generic executor 자체가 멈춘 것은 아니다
  - same executor에 올린 sentinel은 정상 실행되지만 connector `AbstractRunnable connectionAttempt` body만 전혀 시작되지 않는다
- 다음 직접 질문은 `why only the connector AbstractRunnable is silently suppressed/cancelled even though the same generic executor runs the sentinel tasks`다


2026-05-05 plain-runnable vs abstractrunnable split update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.v7kBTX/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_plain_runnable_runs_but_abstractrunnable_does_not.py`
- 결과:
  - `post_submit_sentinel_ran=1`
  - `abstract_control_task_ran=0`
  - `abstract_control_task_failure=0`
  - `task_body_entry=0`
  - `task_failure=0`
  - `task_rejection=0`
- 의미:
  - same generic executor에 올린 plain `Runnable` sentinel은 실행된다
  - 하지만 no-op `AbstractRunnable` control과 connector `connectionAttempt`는 둘 다 body entry가 전혀 없다
  - 따라서 current blocker는 `connectionAttempt` instance 특이 suppression보다 generic executor의 `AbstractRunnable` handling/wrapping contract 쪽으로 더 가깝다
- 주의:
  - 이 run의 top-level `/tmp/java-rust-mixed-membership-abstract-control.latest.json`은 `0-byte` timeout 종료였지만, workdir stdout은 남아 있어 marker split에는 충분했다
- 다음 직접 질문은 `why OpenSearch generic executor runs plain Runnable sentinels but not submitted AbstractRunnable tasks in this regression path`다


2026-05-05 generic executor contract update

- source checker:
  - `/home/ubuntu/steelsearch/tools/check_generic_executor_contract_points_to_wrap_or_silent_queue.py`
  - sources:
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/threadpool/ThreadPool.java`
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/common/util/concurrent/OpenSearchThreadPoolExecutor.java`
    - `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/common/util/concurrent/TimedRunnable.java`
  - actual stdout:
    - `/tmp/java-rust-mixed-membership.v7kBTX/opensearch/stdout.log`
- 결과:
  - `source_generic_silent_queue_warning=True`
  - `source_execute_wraps_context=True`
  - `source_timedrunnable_runs_original=True`
  - `post_submit_sentinel_ran=1`
  - `abstract_control_task_ran=0`
  - `task_body_entry=0`
  - `task_failure=0`
  - `task_rejection=0`
- 의미:
  - source상 generic executor는 shutdown edge에서 task를 `silently queue it and not run it` 할 수 있다
  - submit 경로는 `wrapRunnable()->preserveContext()`를 먼저 거친다
  - actual artifact에서는 explicit rejection/onFailure 없이 plain sentinel만 실행되고 `AbstractRunnable`들은 미실행이므로, 다음 split은 rejection path가 아니라 `preserveContext wrap 이후 queue/termination edge` 쪽이다
- 다음 직접 질문은 `whether the submitted AbstractRunnable actually enters the executor queue and then survives or gets stranded across the generic executor shutdown/lifecycle edge`다


2026-05-05 executor queue vs shutdown edge update

- executor marker artifact:
  - `/tmp/java-rust-mixed-membership.QOHlsI/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_executor_submit_points_away_from_shutdown_queue_edge.py`
- 결과:
  - `after_count=1`
  - `shutdown_true=0`
  - `terminating_true=0`
  - `terminated_true=0`
  - `queued_after_submit_true=0`
- 의미:
  - `after_super_execute` 시점에 executor는 shutdown/terminating 상태가 아니다
  - queue snapshot에도 connector task가 남아 있지 않다
  - 따라서 current blocker는 `silent queue-on-shutdown`보다 `direct handoff 후 worker-start gap` 쪽으로 더 가깝다
- 주의:
  - top-level `/tmp/java-rust-mixed-membership-executor-queue.latest.json`는 `0-byte`였지만, workdir stdout marker는 남아 queue/termination split에는 충분했다
- 다음 직접 질문은 `why the direct-handoff connector task never reaches executor worker-start/beforeExecute despite super.execute() returning normally`다


2026-05-05 beforeExecute boundary update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.11xU0Z/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_before_execute_reaches_connector_but_not_task_body.py`
- 결과:
  - `before_execute_connector=3`
  - `before_execute_plain=0`
  - `before_execute_abstract_control=0`
  - `task_body_entry=0`
  - `task_failure=0`
  - `task_rejection=0`
- 의미:
  - connector task는 generic worker thread `beforeExecute`까지는 실제로 도달한다
  - 그러나 `connectionAttempt.doRun()` 첫 줄 marker는 여전히 0이다
  - 따라서 current blocker는 handoff/worker-start 이전이 아니라 `beforeExecute` 이후 `original.run()` 이전 경계다
- 주의:
  - top-level `/tmp/java-rust-mixed-membership-before-execute.latest.json`는 `0-byte` timeout 종료였지만, workdir stdout marker는 남아 split에는 충분했다
- 다음 직접 질문은 `whether the connector task disappears inside preserveContext/TimedRunnable/context-restoration before original.doRun starts`다


2026-05-05 context wrapper boundary update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.SaU1CL/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_context_wrapper_reaches_inner_dorun_boundary.py`
- 결과:
  - `before_execute_connector=3`
  - `timed_before_original_run=0`
  - `context_doRun_entry=1`
  - `context_after_stash=1`
  - `context_after_restore=1`
  - `context_before_inner_dorun=1`
  - `task_body_entry=0`
- 의미:
  - `ContextPreservingAbstractRunnable.doRun()`은 실제로 진입하고
  - `creatorsContext.restore()`도 통과하며
  - `in.doRun()` 직전 marker까지 남긴다
  - 그런데 원래 task의 첫 줄 marker는 여전히 0이다
- 결론:
  - current blocker는 `preserveContext` wrapper 바깥이 아니라 `connectionAttempt.doRun()` call entry 자체다
- 주의:
  - top-level `/tmp/java-rust-mixed-membership-wrapper-stage.latest.json`는 `0-byte` timeout 종료였지만, workdir stdout marker는 남아 split에는 충분했다
- 다음 직접 질문은 `why the call into connectionAttempt.doRun() itself fails to emit even the first logger marker after ContextPreservingAbstractRunnable reaches before_inner_doRun`다


2026-05-05 anonymous inner class overlay update

- build output:
  - `/home/ubuntu/OpenSearch/server/build/classes/java/main/org/opensearch/discovery/HandshakingTransportAddressConnector$1.class`
- comparison artifacts:
  - old: `/tmp/java-rust-mixed-membership.SaU1CL/opensearch/stdout.log`
  - new: `/tmp/java-rust-mixed-membership.RbTezp/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_inner_class_overlay_restores_task_body_marker.py`
- 결과:
  - `old_task_body_entry=0`
  - `new_task_body_entry=1`
  - `new_open_request=1`
- 의미:
  - `connectionAttempt.doRun()` marker는 outer class가 아니라 anonymous inner class `$1`에 들어 있다
  - outer class만 overlay한 earlier runs에서 `task_body_entry=0`이었던 이유는 runtime suppression이 아니라 inner class overlay omission이다
  - `$1.class`까지 overlay하자 marker가 즉시 복구된다
- 다음 직접 질문은 `which of the earlier worker/context gap conclusions were artifact-side illusions caused by incomplete inner-class overlay, and what the connector path looks like once analysis is redone with full inner-class overlays`다


2026-05-05 full inner-class overlay stop-point reset

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.RbTezp/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_full_inner_overlay_moves_stop_point_to_open_connection_callback.py`
- 결과:
  - `task_body_entry=1`
  - `open_request=1`
  - `open_response=0`
  - `open_failure=0`
  - `probe_stage=0`
  - `connection_response=0`
  - `connection_failure=0`
- 의미:
  - incomplete inner-class overlay에 근거한 worker/context gap 결론은 더 이상 유지되지 않는다
  - full inner-class overlay 기준 current direct stop point는 `connectionAttempt.doRun()` 이전이 아니라 `transportService.openConnection(...).onResponse/onFailure` callback 경계다
- 다음 직접 질문은 `why openConnection request is emitted but neither openConnection onResponse nor onFailure callback ever appears in the full inner-class overlay run`다


2026-05-05 deeper openConnection callback-inner overlay update

- comparison artifacts:
  - base: `/tmp/java-rust-mixed-membership.RbTezp/opensearch/stdout.log`
  - deeper: `/tmp/java-rust-mixed-membership.rfcjCW/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_openconnection_callback_not_restored_by_deeper_inner_overlay.py`
- 결과:
  - `base_open_response=0`
  - `base_open_failure=0`
  - `deeper_open_request=1`
  - `deeper_open_response=0`
  - `deeper_open_failure=0`
- 의미:
  - `openConnection` callback marker 부재는 `$1$1.class` overlay omission 때문은 아니다
  - full inner-class overlay 이후 current stop point는 여전히 `openConnection request` 이후 callback 경계다
- 다음 직접 질문은 `why TransportService.openConnection/TcpTransport callback path itself never emits onResponse/onFailure after the request is issued`다


2026-05-05 transport open callback boundary update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.70s9xm/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_transport_open_stops_before_channels_opened.py`
- 결과:
  - `delegate_to_connection_manager=1`
  - `tcp_open_enter=1`
  - `channels_opened=0`
  - `listeners_attached=0`
  - `timeout_scheduled=0`
- 의미:
  - current path는 `TransportService.openConnection -> connectionManager.openConnection -> TcpTransport.openConnection`까지는 실제로 들어간다
  - 그러나 `TcpTransport.initiateConnection()`의 channel opening loop를 끝내지 못해 `channels_opened` marker조차 남기지 못한다
  - 따라서 current stop point는 callback listener 경계보다 앞, `initiateChannel()` 또는 immediate exception path` 쪽이다
- 주의:
  - top-level `/tmp/java-rust-mixed-membership-transport-open.latest.json`는 `0-byte` timeout 종료였지만, workdir stdout marker는 남아 split에는 충분했다
- 다음 직접 질문은 `what immediate path inside TcpTransport.initiateConnection() prevents even channels_opened from being emitted after TcpTransport.openConnection() is entered`다


2026-05-05 initiateChannel boundary update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.UXPnFS/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_initiate_channel_exception_boundary.py`
- 결과:
  - `before_initiate=1`
  - `after_initiate=0`
  - `connect_exception=0`
  - `general_exception=0`
  - `netty_enter=1`
  - `netty_return=0`
- 의미:
  - `TcpTransport.initiateConnection()`은 실제로 `initiateChannel()` call site까지 도달한다
  - `Netty4Transport.initiateChannel()` body entry도 실제로 시작된다
  - 하지만 `initiateChannel()` return marker와 `TcpTransport` 쪽 immediate exception marker는 모두 0이다
- 결론:
  - current stop point는 `TcpTransport.initiateConnection()` outer loop가 아니라 `Netty4Transport.initiateChannel()` 내부 또는 그 하위 immediate path다
- 주의:
  - top-level `/tmp/java-rust-mixed-membership-initiate-channel.latest.json`는 `0-byte` timeout 종료였지만, workdir stdout marker는 남아 split에는 충분했다
- 다음 직접 질문은 `whether the stop happens inside Netty4 bootstrap.connect()/ChannelFuture creation/channel-null path before initiateChannel can return`다


2026-05-05 Netty4 bootstrap.connect boundary update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.B6y4OI/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_netty4_initiate_channel_connect_boundary.py`
- 결과:
  - `enter=1`
  - `before_connect=1`
  - `after_connect=0`
  - `after_channel_fetch=0`
  - `channel_null=0`
  - `returned=0`
- 의미:
  - `Netty4Transport.initiateChannel()`은 실제로 시작된다
  - `bootstrapWithHandler.connect()` call 직전 marker도 실제로 남는다
  - 하지만 `connect()` return 이후 marker는 하나도 남지 않는다
- 결론:
  - current stop point는 `ChannelFuture` 후처리나 `channel == null` branch가 아니라 `bootstrap.connect()` call 내부다
- 주의:
  - top-level `/tmp/java-rust-mixed-membership-netty4-connect-boundary.latest.json`의 성공 여부와 무관하게 workdir stdout marker는 남아 split에는 충분했다
- 다음 직접 질문은 `where inside Netty Bootstrap.connect()/doResolveAndConnect()/registration path the call stops before returning a ChannelFuture`다


2026-05-05 Netty4 register-vs-connect split update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.7Ki4xR/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_netty4_register_vs_connect_boundary.py`
- 결과:
  - `enter=1`
  - `before_register=1`
  - `after_register=0`
  - `after_register_channel_fetch=0`
  - `register_channel_null=0`
  - `before_channel_connect=0`
  - `after_channel_connect=0`
  - `after_channel_fetch=0`
  - `returned=0`
- 의미:
  - `Netty4Transport.initiateChannel()`은 실제로 `Bootstrap.register()` call 직전까지는 간다
  - 하지만 `register()` 자체가 return하지 않으므로 `channel.connect(...)` 단계로는 아직 내려가지 못한다
- 결론:
  - current stop point는 broad `bootstrap.connect()` 내부가 아니라 더 앞선 `Bootstrap.register()` future return 내부다
- 주의:
  - same run에서 connector path marker는 `task_body_entry=1`, `open_request=1`로 유지되므로 regression이 upstream self-bootstrap으로 후퇴한 run은 아니다
- 다음 직접 질문은 `whether the stall is inside Netty initAndRegister/channel factory/event-loop registration before register() can return a ChannelFuture`다


2026-05-05 Netty4 newChannel-vs-register split update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.IjaY9n/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_netty4_newchannel_vs_register_boundary.py`
- 결과:
  - `enter=1`
  - `before_new_channel=1`
  - `after_new_channel=0`
  - `before_group_register=0`
  - `after_group_register=0`
  - `after_register_channel_fetch=0`
  - `before_channel_connect=0`
  - `returned=0`
- 의미:
  - `Netty4Transport.initiateChannel()`은 실제로 `channelFactory.newChannel()` call 직전까지는 도달한다
  - 하지만 `newChannel()` 자체가 return하지 않으므로 event-loop registration으로는 아직 내려가지 못한다
- 결론:
  - current stop point는 `Bootstrap.register()` 내부 중에서도 더 앞선 `channelFactory.newChannel()` 내부다
- 다음 직접 질문은 `whether the stall is inside ReflectiveChannelFactory.newChannel(), NioSocketChannel construction, or some constructor-side init side effect before newChannel() returns`다


2026-05-05 Netty4 direct constructor experiment update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.CxKn8Q/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_netty4_direct_ctor_boundary.py`
- same-run connector status:
  - `task_body_entry=1`
  - `open_request=1`
  - `open_response=0`
  - `open_failure=0`
- 결과:
  - `enter=1`
  - `before_direct_ctor=0`
  - `after_direct_ctor=0`
  - `before_group_register=0`
  - `after_group_register=0`
  - `before_channel_connect=0`
  - `returned=0`
- 의미:
  - same run은 connector/open request까지는 실제로 진행된다
  - 그러나 direct `new Netty4NioSocketChannel()` experiment에서도 constructor 직전 marker가 전혀 찍히지 않는다
- 결론:
  - current run에서는 `ReflectiveChannelFactory.newChannel()` vs direct constructor split으로 내려가기 전에 이미 `clientBootstrap.clone()/handler()/remoteAddress()` preamble 쪽에서 멈춘다
  - 따라서 direct-constructor experiment는 constructor stall을 확정하기보다, same path가 run-to-run으로 더 이른 preamble 경계에서 멈출 수 있음을 보여준다
- 다음 직접 질문은 `which pre-constructor step among clientBootstrap.clone(), handler(...), and remoteAddress(...) is now the actual stop point in the same connector-path run`다


2026-05-05 Netty4 preamble boundary update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.v5dQ38/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_netty4_preamble_boundary.py`
- same-run connector status:
  - `task_body_entry=1`
  - `open_request=1`
  - `open_response=0`
  - `open_failure=0`
- 결과:
  - `enter=1`
  - `before_clone=1`
  - `after_clone=1`
  - `before_handler=1`
  - `after_handler=0`
  - `before_remote_address=0`
  - `after_remote_address=0`
  - `before_direct_ctor=0`
- 의미:
  - current same run에서는 `clientBootstrap.clone()`은 실제로 return한다
  - stop point는 그 다음 preamble step인 `handler(getClientChannelInitializer(...))` 내부다
- 결론:
  - current direct blocker는 broad preamble 전체가 아니라 `Bootstrap.handler(...)` 또는 `getClientChannelInitializer(node)` 생성 경계로 더 좁혀진다
- 다음 직접 질문은 `whether the stop occurs while constructing getClientChannelInitializer(node) itself or inside Bootstrap.handler(...) setter path after the initializer is produced`다


2026-05-05 Netty4 handler-boundary + same-run continuation update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.l2LWEB/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_netty4_handler_boundary.py`
- same-run preamble follow-up:
  - `after_remote_address=1`
  - `before_direct_ctor=1`
- same-run direct-ctor follow-up:
  - `after_direct_ctor=0`
  - `before_group_register=0`
- 결과:
  - handler checker:
    - `after_clone=1`
    - `before_get_client_initializer=1`
    - `after_get_client_initializer=1`
    - `before_handler_setter=1`
    - `after_handler_setter=1`
    - `before_remote_address=1`
  - direct-ctor checker:
    - `before_direct_ctor=1`
    - `after_direct_ctor=0`
- 의미:
  - current same run에서는 `getClientChannelInitializer(node)` 생성과 `Bootstrap.handler(...)` setter path가 모두 실제로 통과한다
  - same run stop point는 다시 `Netty4NioSocketChannel` direct constructor 내부로 내려간다
- 결론:
  - earlier handler-boundary suspicion은 current same-run evidence로 해소됐고, direct blocker는 다시 constructor 내부다
- 다음 직접 질문은 `which part of Netty4NioSocketChannel/NioSocketChannel constructor path blocks before the direct constructor can return`다


2026-05-05 Netty4NioSocketChannel super-constructor boundary update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.3HVUYY/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_netty4_nio_ctor_super_boundary.py`
- same-run continuity:
  - preamble checker:
    - `after_remote_address=1`
    - `before_direct_ctor=1`
  - direct-ctor checker:
    - `after_direct_ctor=0`
- 결과:
  - `before_direct_ctor=1`
  - `after_direct_ctor=0`
  - `after_super_default_ctor=0`
  - `after_super_parent_socket_ctor=0`
- 의미:
  - current rerun은 direct constructor call site까지는 실제로 도달한다
  - 그러나 `Netty4NioSocketChannel()` body의 `super()` 직후 marker가 전혀 남지 않는다
- 결론:
  - current direct blocker는 `Netty4NioSocketChannel` body 이후가 아니라 `NioSocketChannel super()` constructor 내부다
- 다음 직접 질문은 `which part of the NioSocketChannel constructor path (selector provider open / newSocket / java channel init side effect) blocks before super() returns`다


2026-05-05 open-vs-wrap experiment regression update

- fresh artifacts:
  - `/tmp/java-rust-mixed-membership.7DYHCi/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.9Fo4sR/opensearch/stdout.log`
- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_nio_socketchannel_open_vs_wrap_boundary.py`
- same-run connector status:
  - `task_body_entry=1`
  - `open_request=1`
  - `open_response=0`
  - `open_failure=0`
- 결과:
  - `before_open_socket_channel=0`
  - `after_open_socket_channel=0`
  - `before_direct_ctor=0`
  - `after_direct_ctor=0`
  - `after_super_parent_socket_ctor=0`
- 의미:
  - same connector path run임에도, raw `SocketChannel` open marker까지는 실제로 내려가지 못했다
  - 따라서 open-vs-wrap experiment는 selector provider vs wrapper split을 직접 고정하기 전에 current patched path가 더 이른 경계로 다시 후퇴할 수 있음을 보여준다
- 결론:
  - current uncertainty는 `SelectorProvider.openSocketChannel()` 내부 자체보다, 그 marker에 도달하기 전 경계가 nondeterministically 다시 무너진다는 점이다
- same-artifact reread:
  - `/tmp/java-rust-mixed-membership.7DYHCi/opensearch/stdout.log`
  - `after_clone=0`
  - `before_remote_address=0`
  - `after_remote_address=0`
- updated meaning:
  - at least this concrete regression sample does not fall back between `after_remote_address` and `before_open_socket_channel`
  - it falls back earlier, inside `clientBootstrap.clone()`
- 다음 직접 질문은 `why some runs reach direct-constructor depth while regression samples fall back as early as clientBootstrap.clone()`다


2026-05-05 Bootstrap.clone source-vs-actual divergence update

- source contract (`javap -c -p io.netty.bootstrap.Bootstrap`):
  - `clone()`:
    - `new Bootstrap(this)`
  - private copy constructor:
    - `AbstractBootstrap.<init>(AbstractBootstrap)`
    - `new BootstrapConfig(this)`
    - field copy only:
      - `externalResolver`
      - `disableResolver`
      - `remoteAddress`
- actual comparison:
  - deeper run:
    - `/tmp/java-rust-mixed-membership.3HVUYY/opensearch/stdout.log`
    - `after_clone=1`
    - `before_direct_ctor=1`
  - regression run:
    - `/tmp/java-rust-mixed-membership.7DYHCi/opensearch/stdout.log`
    - `after_clone=0`
- 의미:
  - source상 `Bootstrap.clone()` 자체에는 explicit IO, socket open, registration path가 없다
  - 그런데 same overlay set 아래 actual artifact는 clone boundary에서 갈린다
- 결론:
  - current divergence는 deterministic `Bootstrap.clone()` state/copy semantics보다 broader run-to-run nondeterminism 또는 overlay/logging side effect 쪽으로 더 가깝다
- 남은 불명확점:
  - same overlay set에서도 clone boundary가 갈리는 직접 이유가 logger/overlay timing effect인지, 더 일반적인 runtime nondeterminism인지


2026-05-05 same-overlay A/B compare update

- fresh actual checker:
  - `/home/ubuntu/steelsearch/tools/check_same_overlay_ab_points_to_runtime_nondeterminism.py`
- compared artifacts:
  - deeper run:
    - `/tmp/java-rust-mixed-membership.3HVUYY/opensearch/stdout.log`
  - regression run:
    - `/tmp/java-rust-mixed-membership.7DYHCi/opensearch/stdout.log`
- 결과:
  - deeper:
    - `task_body_entry=1`
    - `open_request=1`
    - `before_clone=1`
    - `after_clone=1`
    - `before_direct_ctor=1`
  - regression:
    - `task_body_entry=1`
    - `open_request=1`
    - `before_clone=1`
    - `after_clone=0`
    - `before_direct_ctor=0`
- 의미:
  - same overlay set에서도 connector entry marker는 동일하게 살아 있다
  - 그런데 clone/depth marker만 run-to-run으로 갈린다
- 결론:
  - current divergence는 overlay omission보다 broader runtime nondeterminism 쪽으로 더 강하게 기운다
- 다음 직접 질문은 `which runtime context before clientBootstrap.clone() changes between the deeper and regression runs enough to flip the stop point while keeping the same connector entry markers alive`다


2026-05-05 pre-clone context first fresh regression sample

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.wL83sA/opensearch/stdout.log`
- marker fields:
  - `thread=opensearch[java-primary-1][generic][T#2]`
  - `threadId=34`
  - `interrupted=false`
  - `bootstrapHash=1314491256`
  - `configHash=1249792747`
  - `groupHash=1486322747`
  - `handlerHash=0`
  - `channelFactory=io.netty.channel.ReflectiveChannelFactory`
  - `remote=/127.0.0.1:45871`
- outcome:
  - `after_clone=0`
  - `before_direct_ctor=0`
- 의미:
  - current marker set으로 regression-side pre-clone context actual capture는 확보됐다
- 남은 불명확점:
  - same marker set의 deeper counterpart가 아직 없어, above context가 deeper run과 truly same인지/다른지 actual A/B로는 아직 닫히지 않았다
- 다음 직접 질문은 `capture one fresh deeper run under the same pre-clone context marker set and compare whether the context is identical despite divergent clone outcome`다


2026-05-05 same-marker rerun still regresses at clone

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.vLdnVJ/opensearch/stdout.log`
- actual reread:
  - `task_body_entry=1`
  - `open_request=1`
  - preamble checker:
    - `after_clone=0`
    - `before_direct_ctor=0`
    - `checker_result=stop_point_is_inside_clientBootstrap_clone`
- 의미:
  - same marker set으로 deeper counterpart를 잡으려 한 first rerun도 clone regression으로 끝났다
- 남은 불명확점:
  - same-marker deeper pair를 아직 확보하지 못했으므로, pre-clone context가 truly 같아도 outcome이 갈리는지 actual A/B는 여전히 미완이다


2026-05-05 same-marker retry loop update

- additional artifacts:
  - `/tmp/java-rust-mixed-membership.Xop45I/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.TnEd0g/opensearch/stdout.log`
- observed outcomes:
  - `Xop45I`:
    - `after_clone=0`
    - `before_direct_ctor=0`
  - `TnEd0g`:
    - `after_clone=1`
    - `before_direct_ctor=0`
- pre-clone compare (`wL83sA` vs `TnEd0g`):
  - same:
    - `thread=opensearch[java-primary-1][generic][T#2]`
    - `threadId=34`
    - `interrupted=false`
    - `handlerHash=0`
    - `channelFactory=io.netty.channel.ReflectiveChannelFactory`
  - different:
    - `bootstrapHash`
    - `configHash`
    - `groupHash`
    - `remote`
- 의미:
  - same marker set 아래 clone boundary outcome 자체도 `after_clone=0`과 `after_clone=1` 사이에서 흔들린다
  - 하지만 still no sample with `before_direct_ctor=1`, so the intended deeper counterpart is still missing
- 남은 불명확점:
  - above differing identity hashes are expected per-run object identity churn, but without a `before_direct_ctor=1` pair they still do not close the question of whether equal pre-clone context can coexist with divergent depth outcomes


2026-05-05 extended same-marker retry loop update

- additional artifacts:
  - `/tmp/java-rust-mixed-membership.e9QGxF/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.u0VEXq/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.cjMqgc/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.peAFhY/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.zDJXCC/opensearch/stdout.log`
- observed outcomes:
  - `e9QGxF`: `after_clone=0`, `before_direct_ctor=0`
  - `u0VEXq`: `after_clone=0`, `before_direct_ctor=0`
  - `cjMqgc`: `after_clone=1`, `before_direct_ctor=0`
  - `peAFhY`: `after_clone=0`, `before_direct_ctor=0`
  - `zDJXCC`: `after_clone=1`, `before_direct_ctor=0`
- 의미:
  - same marker set 아래 clone boundary는 계속 `0/1`로 흔들리지만
  - `before_direct_ctor=1` sample은 이번 extended retry loop에서도 여전히 나오지 않았다
- 결론:
  - current blocker is no longer “whether clone outcome fluctuates”; that is already established
  - the blocker is failure to obtain a same-marker deeper counterpart reaching direct-constructor depth


2026-05-05 extra retry sequence update

- additional artifacts:
  - `/tmp/java-rust-mixed-membership.ae4F2d/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.LI7XRq/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.8CPSaF/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.MDIIaO/opensearch/stdout.log`
  - `/tmp/java-rust-mixed-membership.NE19Rh/opensearch/stdout.log`
- observed outcomes:
  - all five:
    - `after_clone=0`
    - `before_direct_ctor=0`
- 의미:
  - additional short-timeout retries did not produce even `after_clone=1` this time
  - regression-side clone stop remained dominant across this extra sequence
- 남은 불명확점:
  - same-marker deeper counterpart is still missing, so the original target comparison remains open


2026-05-05 longer-timeout same-marker pair update

- fresh artifact:
  - `/tmp/java-rust-mixed-membership.F09x4h/opensearch/stdout.log`
- same-pair compare target:
  - regression baseline:
    - `/tmp/java-rust-mixed-membership.wL83sA/opensearch/stdout.log`
- results:
  - `F09x4h`:
    - `after_clone=1`
    - `before_direct_ctor=0`
  - compare (`wL83sA` vs `F09x4h`):
    - same:
      - `thread=opensearch[java-primary-1][generic][T#2]`
      - `threadId=34`
      - `interrupted=false`
      - `handlerHash=0`
      - `channelFactory=io.netty.channel.ReflectiveChannelFactory`
    - different:
      - `bootstrapHash`
      - `configHash`
      - `groupHash`
      - `remote`
- 의미:
  - same marker set 아래, and with the same generic thread context fields, clone-boundary outcome itself can differ (`after_clone=0` vs `after_clone=1`)
  - so the clone-boundary divergence target is now sufficiently fixed
  - the remaining blocker moves one step deeper: why even the `after_clone=1` sample still stalls before `before_direct_ctor`
- 다음 직접 질문은 `what splits the post-clone path among the same-marker after_clone=1 samples before they reach before_direct_ctor`다
## 2026-05-05 same-marker post-clone depth divergence update

- same-marker `after_clone=1` sample들을 다시 모으면:
  - `/tmp/java-rust-mixed-membership.F09x4h`: `before_get_client_initializer=1`
  - `/tmp/java-rust-mixed-membership.TnEd0g`: `before_get_client_initializer=0`
  - `/tmp/java-rust-mixed-membership.cjMqgc`: `before_get_client_initializer=1`
  - `/tmp/java-rust-mixed-membership.zDJXCC`: `before_get_client_initializer=1`
- 그러나 네 sample 모두 `after_get_client_initializer=0`, `after_handler_setter=0`, `before_direct_ctor=0`이다.
- 따라서 current same-marker deeper stop은 broad post-clone path 전체보다 `getClientChannelInitializer(node)` entry/exit boundary로 보는 편이 맞다.
- 남은 질문:
  - `getClientChannelInitializer(node)` 내부에서 block되는 것인지
  - 아니면 initializer 생성 직전/직후 logging omission이 있는 것인지
  - 그리고 `TnEd0g`처럼 `after_clone=1`인데 `before_get_client_initializer=0`인 shallower variant를 같은 root-cause family로 볼 수 있는지

## 2026-05-05 initializer-stage fresh regression note

- initializer stage marker를 넣고 다시 돌린 fresh probe `/tmp/java-rust-mixed-membership.q0BogF/opensearch/stdout.log`에서는
  - `steelsearch_connector_stage=task_body_entry=1`
  - `steelsearch_open_connection_stage=request=1`
  - `steelsearch_netty4_open_stage=initiateChannel_enter=1`
  까지는 보이지만,
  - `steelsearch_netty4_open_stage=pre_clone_context=0`
  - `steelsearch_netty4_initializer_stage=* = 0`
  이다.
- 따라서 initializer 경계를 더 내린 instrumentation 자체는 들어갔지만, fresh run은 오히려 그 marker들 직전으로 다시 후퇴했다.
- 남은 질문:
  - 이것이 same broader runtime nondeterminism의 얕은 variant인지
  - 아니면 `pre_clone_context` 이후 marker set이 timeout 종료에서 유실될 수 있는지

## 2026-05-05 constructor-boundary narrowing update

- current instrumented source의 `getClientChannelInitializer(node)`는 실제로
  - `ClientChannelInitializer initializer = new ClientChannelInitializer();`
  - `return initializer;`
  구조다.
- actual same-marker sample `/tmp/java-rust-mixed-membership.F09x4h`, `/tmp/java-rust-mixed-membership.TnEd0g`, `/tmp/java-rust-mixed-membership.cjMqgc`, `/tmp/java-rust-mixed-membership.zDJXCC`에서는
  - `before_get_client_initializer=3/4`
  - `after_get_client_initializer=0/4`
  - `after_handler_setter=0/4`
  였다.
- 따라서 old question인 `initializer 생성 vs handler setter`는 닫혔고, current deeper stop은 `ClientChannelInitializer` construction boundary로 보는 편이 맞다.
- 다만 fresh initializer-marker retries(`/tmp/java-rust-mixed-membership.q0BogF`, `/tmp/java-rust-mixed-membership.RyRuO7`, `/tmp/java-rust-mixed-membership.4Ak9Vi`, `/tmp/java-rust-mixed-membership.O8qUSH`, `/tmp/java-rust-mixed-membership.wmc1Fb`)는 `initializer_stage=method_entry`를 다시 못 재현했다.
- 남은 질문:
  - fresh run에서 constructor-boundary sample을 다시 확보하지 못하는 이유가 broader runtime nondeterminism dominance인지
  - 아니면 current timeout/probe window가 too short해서 `initializer_stage=*`를 놓치는지

## 2026-05-05 useful initializer-stage sample recovered

- longer-timeout retry sequence의 third sample `/tmp/java-rust-mixed-membership.yNRvAY/opensearch/stdout.log`에서는 finally
  - `before_clone=1`
  - `after_clone=1`
  - `before_get_client_initializer=1`
  - `after_get_client_initializer=1`
  - `method_entry=1`
  - `before_new_client_initializer=1`
  - `after_new_client_initializer=1`
  - `method_return=1`
  이 모두 관측됐다.
- 그러나 같은 sample에서 `client_initializer_ctor_body=0`이다.
- 이 조합은 runtime constructor stall보다는 `Netty4Transport$ClientChannelInitializer.class` marker coverage omission 쪽이 더 직접적이라는 뜻이다.
- 남은 질문:
  - inner-class overlay를 실제로 포함하면 `client_initializer_ctor_body`가 즉시 복구되는지
  - 복구된다면 constructor body 이후 actual next stop point가 어디인지

## 2026-05-05 inner-class-overlay retry note

- `Netty4Transport$ClientChannelInitializer.class`를 overlay spec에 추가한 fresh retries:
  - `/tmp/java-rust-mixed-membership.WbQcxG`
  - `/tmp/java-rust-mixed-membership.2wB12n`
  - `/tmp/java-rust-mixed-membership.MSP9es`
- observed markers:
  - `WbQcxG`: useful marker 없음
  - `2wB12n`: `before_clone=1`
  - `MSP9es`: useful marker 없음
- 즉 inner-class overlay를 실제로 추가했지만, 이번 retry set에서는 `method_entry` 자체가 다시 안 잡혀서 `client_initializer_ctor_body` 복구 여부를 판정할 sample을 못 얻었다.
- 남은 질문:
  - current blocker가 inner-class overlay correctness가 아니라 same runtime nondeterminism에 의한 sample scarcity인지
  - useful sample을 다시 얻기 위한 retry 조건(더 긴 timeout, 다른 cadence, probe sequencing)이 필요한지

## 2026-05-05 extended inner-class-overlay retries

- extended retry set:
  - `/tmp/java-rust-mixed-membership.T8ygpj`
  - `/tmp/java-rust-mixed-membership.JJEBDS`
  - `/tmp/java-rust-mixed-membership.sS8bOY`
  - `/tmp/java-rust-mixed-membership.uJ23Kx`
  - `/tmp/java-rust-mixed-membership.tuT8sp`
- observed markers:
  - `T8ygpj`: useful marker 없음
  - `JJEBDS`: `before_clone=1`
  - `sS8bOY`: useful marker 없음
  - `uJ23Kx`: useful marker 없음
  - `tuT8sp`: useful marker 없음
- 따라서 inner-class overlay를 실제로 넣고 retry count를 늘려도 useful sample scarcity가 계속 앞단을 지배한다.
- 남은 질문:
  - retry strategy 자체를 바꾸지 않으면 `client_initializer_ctor_body` sample을 계속 못 얻는지
  - useful sample scarcity를 줄이는 probe cadence/timeout/ordering tweak가 필요한지

## 2026-05-05 retry helper added

- `tools/retry_probe_until_initializer_stage.py`를 추가해 inner-class overlay + probe retry 절차를 한 명령으로 고정했다.
- smoke run:
  - `/tmp/java-rust-mixed-membership.xBDQZw`
  - `/tmp/java-rust-mixed-membership.rS38eR`
  - result: `no_useful_initializer_sample`
- 따라서 helper는 준비됐지만, current issue는 절차 부재가 아니라 sample scarcity 자체다.

## 2026-05-05 inner-class overlay useful sample

- helper soak run의 fourth sample `/tmp/java-rust-mixed-membership.LfyzDf/opensearch/stdout.log`에서는 finally
  - `method_entry=1`
  - `before_new_client_initializer=1`
  - `client_initializer_ctor_body=0`
  - `after_new_client_initializer=0`
  - `method_return=0`
  이 관측됐다.
- 따라서 `Netty4Transport$ClientChannelInitializer.class`를 overlay에 넣어도 ctor-body marker는 복구되지 않았고, current stop point는 actual `new ClientChannelInitializer()` call boundary로 보는 편이 맞다.
- 남은 질문:
  - stop point가 `ChannelInitializer` super constructor path인지
  - 아니면 `ClientChannelInitializer` classloading/init edge인지

## 2026-05-05 constructor-path fully recovered sample

- init marker를 더 넣고 돌린 helper soak run의 useful sample `/tmp/java-rust-mixed-membership.tv2qoA/opensearch/stdout.log`에서는
  - `client_initializer_static_init=1`
  - `client_initializer_instance_init=1`
  - `client_initializer_ctor_body=1`
  - `after_new_client_initializer=1`
  - `method_return=1`
  - `after_handler_setter=1`
  - `before_remote_address=1`
  - `after_remote_address=0`
  이 관측됐다.
- 따라서 `new ClientChannelInitializer()` 내부 stop hypothesis는 닫혔고, current downstream stop point는 `Bootstrap.remoteAddress(...)` setter path 쪽으로 이동했다.
- 남은 질문:
  - `remoteAddress(...)` call 자체에서 멈추는지
  - 아니면 `before_remote_address` 이후 broader downstream nondeterminism인지

## 2026-05-05 remoteAddress setter contract update

- Netty `Bootstrap.remoteAddress(SocketAddress)` bytecode는 실제로
  - `aload_0`
  - `aload_1`
  - `putfield remoteAddress`
  - `aload_0`
  - `areturn`
  뿐이다.
- actual sample `/tmp/java-rust-mixed-membership.tv2qoA`는
  - `after_handler_setter=1`
  - `before_remote_address=1`
  - `after_remote_address=0`
  이다.
- 따라서 `remoteAddress(...)`는 complex logic stall point라기보다 call boundary 자체 또는 그 직후 runtime divergence 쪽으로 보는 편이 맞다.
- 남은 질문:
  - same-marker fresh pair에서 `after_remote_address=1` counterpart를 다시 얻을 수 있는지
  - 이 absence가 actual runtime divergence인지, marker/logging omission인지

## 2026-05-05 remote-after soak retry

- `tools/retry_probe_until_initializer_stage.py --stop-at remote_after --attempts 4 --timeout-seconds 120` actual soak run:
  - `/tmp/java-rust-mixed-membership.Q23nyI`
  - `/tmp/java-rust-mixed-membership.RAK6lJ`
  - `/tmp/java-rust-mixed-membership.2iZmNT`
  - `/tmp/java-rust-mixed-membership.ovbVa3`
- observed:
  - `RAK6lJ`: `before_clone=1`
  - others: useful marker 없음
  - final result: `no_useful_sample_for_remote_after`
- 따라서 current first blocker는 `remoteAddress(...)` semantics 자체가 아니라 fresh `after_remote_address=1` counterpart sample scarcity다.

## 2026-05-05 remoteAddress pair recovered

- longer-timeout `--stop-at remote_after` soak run의 second sample `/tmp/java-rust-mixed-membership.bv58xM/opensearch/stdout.log`에서는
  - `after_remote_address=1`
  - `before_open_socket_channel=1`
  이 관측됐다.
- pair compare:
  - left `/tmp/java-rust-mixed-membership.tv2qoA`: `after_remote_address=0`
  - right `/tmp/java-rust-mixed-membership.bv58xM`: `after_remote_address=1`
  - shared prefix는 둘 다 `client_initializer_*`, `after_new_client_initializer`, `method_return`, `after_handler_setter`, `before_remote_address`까지 동일했다.
- 따라서 `remoteAddress(...)` 경계는 logging omission이 아니라 actual runtime divergence로 닫혔다.
- 남은 질문:
  - next stop point가 `SelectorProvider.openSocketChannel()` call boundary인지
  - 아니면 `before_open_socket_channel` 이후 broader downstream divergence인지

## 2026-05-05 openSocketChannel wrapper contract update

- JDK `sun.nio.ch.SelectorProviderImpl.openSocketChannel()` bytecode는 실제로
  - `new SocketChannelImpl`
  - `dup`
  - `aload_0`
  - `invokespecial SocketChannelImpl.<init>(SelectorProvider)`
  - `areturn`
  뿐이다.
- actual sample `/tmp/java-rust-mixed-membership.bv58xM`는
  - `after_remote_address=1`
  - `before_open_socket_channel=1`
  - `after_open_socket_channel=0`
  이다.
- 따라서 `openSocketChannel()` wrapper 자체보다 actual stop point는 `SocketChannelImpl` constructor boundary 쪽으로 더 기운다.
- 남은 질문:
  - `SocketChannelImpl` constructor 안의 super/Net/socket-init path 중 어디서 멈추는지

## 2026-05-05 SocketChannelImpl ctor chain update

- JDK `SocketChannelImpl(SelectorProvider)` one-arg ctor는 실제로
  - IPv4/IPv6 family 선택
  - `SocketChannelImpl(SelectorProvider, ProtocolFamily)` 호출
  만 수행한다.
- two-arg ctor는
  - `SocketChannel.<init>(provider)`
  - lock/object field init
  - `family` validation
  - `Net.socket(family, true)`
  - `IOUtil.fdVal(fd)`
  순서로 진행된다.
- actual sample `/tmp/java-rust-mixed-membership.bv58xM`는 `before_open_socket_channel=1`, `after_open_socket_channel=0`이므로, current direct split은 one-arg wrapper가 아니라 two-arg ctor 내부의 `super` vs `Net.socket(...)` 사이다.

## 2026-05-05 super constructor chain update

- `java.nio.channels.SocketChannel.<init>(provider)`는 `AbstractSelectableChannel.<init>(provider)`만 호출한다.
- `AbstractSelectableChannel.<init>(provider)`는
  - `SelectableChannel.<init>()`
  - `keys=null`
  - `keyCount=0`
  - `new Object()` for locks
  - `provider` field set
  만 수행하고 explicit IO는 없다.
- 따라서 actual sample `/tmp/java-rust-mixed-membership.bv58xM`의 `before_open_socket_channel=1`, `after_open_socket_channel=0`은 super chain보다 `Net.socket(family, true)` native socket creation 또는 그 직전 two-arg ctor steps 쪽으로 더 기운다.

## 2026-05-05 pre-Net.socket step update

- `SocketChannelImpl(SelectorProvider, ProtocolFamily)`의 `Net.socket(...)` 이전 구간은
  - lock/object field init
  - `Objects.requireNonNull`
  - family validation
  뿐이며, explicit IO는 `Net.socket(family, true)`에서 처음 나타난다.
- actual sample `/tmp/java-rust-mixed-membership.bv58xM`는 여전히 `before_open_socket_channel=1`, `after_open_socket_channel=0`이다.
- 따라서 current direct stop point는 pre-`Net.socket` Java-side steps보다 `Net.socket(family, true)` native socket creation 자체로 보는 편이 더 맞다.

## 2026-05-05 Net.socket wrapper update

- JDK `sun.nio.ch.Net.socket(ProtocolFamily, boolean)`는 실제로
  - family/IPv6 flag 계산
  - `socket0(ZZZZ)` native call
  - `IOUtil.newFD(int)`
  - `return FileDescriptor`
  순서의 thin wrapper다.
- actual sample `/tmp/java-rust-mixed-membership.bv58xM`는 여전히 `before_open_socket_channel=1`, `after_open_socket_channel=0`이다.
- 따라서 current direct split은 `socket0` native socket creation 또는 직후 `IOUtil.newFD` 쪽으로 더 내려갔다.

## 2026-05-05 IOUtil.newFD wrapper update

- JDK `sun.nio.ch.IOUtil.newFD(int)`는 실제로
  - `new FileDescriptor()`
  - `setfdVal(fd, int)`
  - `return fd`
  순서의 trivial wrapper다.
- source상 `Net.socket(...)`는 `socket0(ZZZZ)` 뒤 `IOUtil.newFD(int)`만 호출하므로, Java-side post-native work는 매우 얇다.
- actual sample `/tmp/java-rust-mixed-membership.bv58xM`는 여전히 `before_open_socket_channel=1`, `after_open_socket_channel=0`이다.
- 따라서 current direct stop point는 `IOUtil.newFD`보다 `socket0(ZZZZ)` native socket creation 자체로 보는 편이 더 맞다.

## 2026-05-05 openSocketChannel pair update

- same-marker pair
  - `/tmp/java-rust-mixed-membership.bv58xM`
  - `/tmp/java-rust-mixed-membership.yNRvAY`
  는 둘 다
  - `task_body_entry`
  - `open_request`
  - `before_clone/after_clone`
  - `before_get_client_initializer/after_get_client_initializer`
  - `before_handler_setter/after_handler_setter`
  - `before_remote_address/after_remote_address`
  - `before_open_socket_channel`
  prefix를 공유한다.
- 그런데 outcome은
  - `bv58xM`: `after_open_socket_channel=0`
  - `yNRvAY`: `after_open_socket_channel=1`
  로 갈린다.
- 또한 `yNRvAY`는 그 뒤 `before_direct_nio_ctor=1`, `after_direct_nio_ctor=0`까지 진행된다.
- 따라서 `before_open_socket_channel=1` 이후의 갈림은 useful-sample scarcity나 prefix marker omission이 아니라 `openSocketChannel` return boundary의 actual runtime divergence로 보는 편이 더 맞다.
- 동시에 useful right branch가 `after_open_socket_channel=1` 직후 바로 `before_direct_nio_ctor=1`까지 진입하므로, current next stop point는 `new Netty4NioSocketChannel(null, rawSocketChannel)` call boundary 자체보다 raw-socket overload ctor 내부라고 보는 편이 더 맞다.

## 2026-05-05 raw-socket overload ctor update

- source상 `Netty4NioSocketChannel(Channel parent, SocketChannel socket)` body에는 `super(parent, socket)` 직후
  - `steelsearch_netty4_nio_ctor_stage=after_super_parent_socket_ctor`
  marker가 있다.
- useful sample `/tmp/java-rust-mixed-membership.yNRvAY`는
  - `before_direct_nio_ctor=1`
  - `after_direct_nio_ctor=0`
  - `after_super_parent_socket_ctor=0`
  이다.
- 따라서 current direct stop point는 raw-socket overload ctor body entry 이후가 아니라 `super(parent, socket)` path 내부로 보는 편이 더 맞다.

## 2026-05-05 NioSocketChannel parent-socket ctor update

- Netty bytecode상 `NioSocketChannel(Channel, SocketChannel)` ctor는
  - `AbstractNioByteChannel.<init>(parent, selectableChannel)`
  - `SocketChannel.socket()`
  - `new NioSocketChannelConfig(...)`
  순서다.
- useful sample `/tmp/java-rust-mixed-membership.yNRvAY`는
  - `before_direct_nio_ctor=1`
  - `after_direct_nio_ctor=0`
  - `after_super_parent_socket_ctor=0`
  이다.
- 따라서 current direct stop point는 `NioSocketChannel` body 진입 이후가 아니라 `AbstractNioByteChannel.<init>` super ctor 쪽으로 보는 편이 더 맞다.

## 2026-05-05 AbstractNioByteChannel ctor update

- Netty bytecode상 `AbstractNioByteChannel(Channel, SelectableChannel)` ctor는
  - `AbstractNioChannel.<init>(parent, selectableChannel, 1)`
  - `new AbstractNioByteChannel$1`
  - `flushTask` field set
  - `return`
  순서다.
- useful sample `/tmp/java-rust-mixed-membership.yNRvAY`는 여전히
  - `before_direct_nio_ctor=1`
  - `after_direct_nio_ctor=0`
  - `after_super_parent_socket_ctor=0`
  이다.
- 따라서 current direct stop point는 `AbstractNioByteChannel` body보다 `AbstractNioChannel.<init>` ctor 또는 그 안의 `configureBlocking(false)` 경계로 보는 편이 더 맞다.

## 2026-05-05 AbstractNioChannel ctor update

- Netty bytecode상 `AbstractNioChannel(Channel, SelectableChannel, int)` ctor는
  - `NioIoOps.valueOf(readInterestOp)`
  - `AbstractNioChannel(Channel, SelectableChannel, NioIoOps)`
  로 즉시 delegate하는 wrapper다.
- 하위 ctor에서 actual IO/exception edge는
  - `SelectableChannel.configureBlocking(false)`
  - 실패 시 `SelectableChannel.close()`
  - `ChannelException("Failed to enter non-blocking mode.")`
  뿐이다.
- useful sample `/tmp/java-rust-mixed-membership.yNRvAY`와 상위 ctor marker 부재를 합치면, current direct stop point는 `AbstractNioChannel` thin wrapper보다 `configureBlocking(false)` 또는 그 failure cleanup path 쪽으로 보는 편이 더 맞다.

## 2026-05-05 configureBlocking contract update

- JDK `AbstractSelectableChannel.configureBlocking(boolean)`는
  - `regLock` 동기화
  - `isOpen()` 검사
  - valid key / blocking mode 검사
  - `implConfigureBlocking(boolean)`
  - `nonBlocking` field update
  계약을 가진다.
- useful sample `/tmp/java-rust-mixed-membership.yNRvAY`에는 Netty-side failure cleanup 흔적
  - `Failed to enter non-blocking mode.`
  - `Failed to close a partially initialized socket.`
  - `ChannelException`
  이 전혀 없다.
- 따라서 current direct stop point는 Java cleanup logging path보다 `implConfigureBlocking(false)` 또는 그 하위 non-blocking native transition 쪽으로 보는 편이 더 맞다.

## 2026-05-05 implConfigureBlocking update

- `SocketChannelImpl.implConfigureBlocking(boolean)`는
  - `readLock.lock()`
  - `writeLock.lock()`
  - `lockedConfigureBlocking(boolean)`
  - unlock
  순서의 lock wrapper다.
- bytecode상 이 경로 아래에는 `IOUtil.configureBlocking(fd, boolean)` 호출이 존재한다.
- useful sample `/tmp/java-rust-mixed-membership.yNRvAY`에 failure cleanup 흔적이 없으므로, current direct stop point는 `implConfigureBlocking` body보다 `lockedConfigureBlocking(false)` 또는 그 하위 `IOUtil.configureBlocking(fd, false)` 쪽으로 보는 편이 더 맞다.

## 2026-05-05 lockedConfigureBlocking update

- `lockedConfigureBlocking(boolean)`는
  - lock assertion
  - `stateLock` monitor
  - trivial `ensureOpen()`
  - `forcedNonBlocking` branch
  - `IOUtil.configureBlocking(fd, boolean)`
  순서의 작은 prelude다.
- `ensureOpen()` 자체는 `isOpen()` false일 때 `ClosedChannelException`만 던지는 trivial check다.
- useful sample `/tmp/java-rust-mixed-membership.yNRvAY`에 failure cleanup 흔적이 없으므로, current direct stop point는 `lockedConfigureBlocking` Java prelude보다 `IOUtil.configureBlocking(fd, false)` 또는 그 하위 native transition 쪽으로 보는 편이 더 맞다.

## 2026-05-05 IOUtil.configureBlocking native update

- JDK `IOUtil.configureBlocking(FileDescriptor, boolean)` 자체는 bytecode body가 없는 `native` method다.
- useful sample `/tmp/java-rust-mixed-membership.yNRvAY`에
  - `Failed to enter non-blocking mode.`
  - `Failed to close a partially initialized socket.`
- `ChannelException`
  흔적이 없으므로, current direct stop point는 Java-side wrapper가 아니라 `IOUtil.configureBlocking(fd, false)` native transition boundary 자체로 보는 편이 더 맞다.
- 여기서부터는 local JDK source 또는 native symbol visibility가 있는지 확인하지 않으면 Java bytecode만으로는 더 못 내려갈 수 있다.

## 2026-05-05 local JDK native visibility update

- local environment에는 JDK `src.zip`이 없다.
- 하지만 `/usr/lib/jvm/java-21-openjdk-arm64/lib/libnio.so`에는 exported symbol
  - `Java_sun_nio_ch_IOUtil_configureBlocking`
- `Java_sun_nio_ch_IOUtil_fdVal`
  가 실제로 존재한다.
- 따라서 current stop point는 여전히 `IOUtil.configureBlocking(fd, false)` native boundary에 고정되며, 더 내려가려면 bytecode가 아니라 native symbol disassembly나 syscall-level 관측이 필요하다.

## 2026-05-05 IOUtil.configureBlocking disassembly update

- `Java_sun_nio_ch_IOUtil_configureBlocking` disassembly는 실제로
  - `fcntl(F_GETFL)`로 current flags를 읽고
  - `O_NONBLOCK(0x800)` bit를 clear/set한 뒤
  - `fcntl(F_SETFL)`로 다시 쓰며
  - 실패 시 `JNU_ThrowIOExceptionWithLastError`로 간다.
- useful sample `/tmp/java-rust-mixed-membership.yNRvAY`에는 여전히 Java-side failure cleanup 흔적이 없다.
- 따라서 current direct stop point는 Java/native wrapper가 아니라 syscall-level `fcntl(F_GETFL/F_SETFL)` non-blocking flag transition까지 내려갔다.

## 2026-05-05 syscall diagnostic availability update

- local environment에는 `strace`가 없다.
- 대체 후보 중 `perf`는 존재하지만
  - `perf trace -e fcntl -- sleep 0`
  가 `raw_syscalls` tracing feature 부재로 실패한다.
- 따라서 현재 세션에서는 dynamic syscall tracing으로 `fcntl(F_GETFL/F_SETFL)` 경계의 stall/error를 직접 관측하기 어렵다.
- 이 지점부터는 static native disassembly를 더 파거나, 현재 syscall-level conclusion을 보존한 채 다른 backlog로 넘어갈지 결정이 필요하다.

## 2026-05-05 native branch practical stop point update

- native branch는 현재 세션에서
  - bytecode -> native symbol -> disassembly -> `fcntl(F_GETFL/F_SETFL)` + `O_NONBLOCK` 토글
  까지 이미 내려갔다.
- 반면 dynamic syscall tracing은
  - `strace` 부재
  - `perf raw_syscalls` tracing feature 부재
  때문에 막혀 있다.
- 따라서 current session에서 이 branch는 practical stop point에 도달했고, 추가 static splitting보다 남은 mixed data-node validation backlog로 pivot하는 편이 더 생산적이다.

## 2026-05-05 rust-primary/java-replica wiring update

- `rust-primary-java-replica` profile fixture는 이미 존재한다.
- 따라서 이번 회차에서는 새 actual runner를 다시 만들지 않고, existing
  - `run_java_primary_rust_replica_actual.py`
  - `run-java-mixed-cluster-binary-harness.sh`
  를 재사용하는 wrapper
  - `run_rust_primary_java_replica_from_probe_report.sh`
  를 추가했다.
- `/tmp/java-rust-mixed-membership-live-5s-success6.handoff.json` 기준 `--print-only` resolved command는
  - `prepare`
  - `write`
  - `read`
  - `recover`
  - `restart`
  - `check`
  phase와 `rust-primary-java-replica/runtime-state` 경로를 모두 정상 구성한다.
- 아직 actual harness execution 자체는 안 했으므로, 다음 직접 work는 collector/provenance 구현 또는 actual test 쪽이다.

## 2026-05-05 replica provenance collector update

- `run_java_primary_rust_replica_actual.py`의 `check` phase에
  - `GET /{index}/_recovery?detailed=true`
  actual 수집을 추가했다.
- 새 `classify_replica_provenance(...)` collector는 replica shard의
  - `index.files.recovered`
  - `translog.recovered_ops` 계열
  값을 보고
  - `segment`
  - `translog`
  - `mixed`
  를 분류한다.
- `JAVA_MIXED_CLUSTER_REPORT_DIR`의 profile name을 읽어
  - `rust-primary-java-replica`에서는 `java_node`
  - 그 외 current Java-primary path에서는 `rust_node`
  를 replica target으로 선택하도록 dispatch를 넣었다.
- synthetic recovery payload smoke에서 `translog`, `segment`, `mixed` 세 mode가 각각 실제로 분류됨을 확인했다.

## 2026-05-05 rust-primary divergence mapping update

- `classify_divergence(...)`는 이제 profile-aware다.
- `rust-primary-java-replica` profile에서는 raw failure classes를 다음으로 remap한다:
  - `apply_mismatch -> acknowledged_but_diverged`
  - `checkpoint_mismatch -> metadata_mismatch`
  - `decode_mismatch -> unsupported_op`
- phase artifact에는
  - `observed_failure_classes`
  - `observed_raw_failure_classes`
  를 함께 남긴다.
- synthetic state smoke에서
  - `apply_mismatch + checkpoint_mismatch -> acknowledged_but_diverged + metadata_mismatch`
  - `decode_mismatch -> unsupported_op`
  가 실제로 확인됐다.
- 2026-05-05: `Rust primary <-> Java replica actual run`을 위해 fresh live probe를 다시 붙였더니, stale handoff `/tmp/java-rust-mixed-membership-live-5s-success6.handoff.json`로는 `Connection refused`가 났고, overlay 없는 fresh probe `/tmp/java-rust-mixed-membership.JD43su`는 `NoClassDefFoundError: HandshakingTransportAddressConnector$2`, `$2`를 추가한 overlay probe `/tmp/java-rust-mixed-membership.OObzwF`는 `NoClassDefFoundError: HandshakingTransportAddressConnector$3`로 죽었다. `HandshakingTransportAddressConnector` anonymous inner classes 전체(`$1`, `$1$1`, `$1$1$1`, `$1$1$1$1`, `$2`, `$3`)를 포함한 full-family overlay set fresh probe `/tmp/java-rust-mixed-membership.J2Ez6F/report.json`에서는 startup crash는 사라졌지만 최종 결과가 `membership_formed=false`, `failure_stage=membership_timeout`, `observed_node_count=0`이었다. 따라서 current direct blocker는 더 이상 classload omission이 아니라, full overlay set 아래 fresh formed 2-node handoff를 다시 복구하는 일이다.
- 2026-05-05: full overlay set 아래 formed handoff 복구를 위해 `retry_probe_until_initializer_stage.py --stop-at formed_membership --attempts 3 --timeout-seconds 240`를 actual로 돌린 결과 `/tmp/java-rust-mixed-membership.QPC57a`, `/tmp/java-rust-mixed-membership.tpgXwj`, `/tmp/java-rust-mixed-membership.bFmjsn` 세 run 모두 `after_open_socket_channel`, `client_initializer_ctor_body` 등 deep transport markers는 `131~132회` 안정적으로 찍혔지만 helper result는 `no_useful_sample_for_formed_membership`이었다. representative sample `/tmp/java-rust-mixed-membership.QPC57a/opensearch/stdout.log`에서는 `cluster-manager not discovered yet`가 반복되고 `have discovered [{java-primary-1}...]`만 보여 Rust node가 discovery roster에 아예 안 들어온다. 즉 current blocker는 connector/open depth regression이 아니라, Java discovery roster에서 Rust node visibility가 사라진 쪽이다.
- 2026-05-05: `/tmp/java-rust-mixed-membership.QPC57a`를 local transport probe artifact까지 묶어 다시 보면, `/steelsearch/transport-connect.json`은 `tcp_connected=true`, `/steelsearch/transport-handshake.json`은 `response_received=true`, `response_starts_with_es=true`다. 즉 probe script의 own TCP+handshake는 same run에서 성공한다. 그런데 같은 run의 `/opensearch/stdout.log`에서는 `steelsearch_open_connection_stage=request=132`, `response=0`, `failure=132`, `Connection refused: /127.0.0.1:39517`가 반복된다. 따라서 current discovery roster absence는 “Rust seed host가 처음부터 unreachable”이 아니라, local probe success 뒤 Rust transport listener가 Java discovery connect 시점에는 refused 상태로 내려가는 lifecycle 문제로 보는 편이 맞다.
- 2026-05-05: 그러나 fresh live probe `/tmp/java-rust-mixed-membership.bS95Q2`에서 `live_handoff_ready` 직후 same workdir의 `steelsearch/pid`와 `start-command.txt`를 직접 점검해 보면 Rust PID는 `alive_now=True`, `alive_after_3s=True`, `alive_after_20s=True`였고 transport port `43211`도 `tcp_now=True`, `tcp_after_3s=True`, `tcp_after_20s=True`, burst connect `20/20 success`였다. 같은 run의 OpenSearch stdout은 `open_failure=125`, `open_response=0`, `handshake_timeout[1s]=91`, `Connection refused=35`를 보여, current direct blocker는 generic process exit나 steady listener drop보다 “local probe의 raw handshake는 성공하지만 Java discovery handshake는 timeout 된다”는 transport handshake divergence 쪽으로 더 직접적이다.
- 2026-05-05: same live run `/tmp/java-rust-mixed-membership.bS95Q2`의 `transport-seed-capture.json`과 OpenSearch stdout을 묶으면, Rust가 본 Java traffic은 `tcp_handshake_only=101`이고 그 `101/101` 모두 response를 보낸 뒤 `follow_up_frame=None` 상태로 끝난다. 동시에 OpenSearch는 `channels_connected_listener_onResponse=100`까지는 가지만 최종 `open_response=0`, `open_failure=134`, `handshake_timeout[1s]=100`이다. 따라서 current failure는 raw TCP handshake 미응답이 아니라, Java discovery path가 `internal:tcp/handshake` 응답까지는 받지만 그 뒤 reusable follow-up handshake/request_peers phase로 넘어가지 못하고 one-shot `remote_eof` lifecycle로 끝나는 mismatch로 보는 편이 맞다.
- 2026-05-05: source `/home/ubuntu/steelsearch/crates/os-node/src/main.rs`를 actual capture와 다시 맞춰 보면 current discovery path의 decisive point는 policy다. source상 `internal:transport/handshake`와 `internal:discovery/request_peers` branch는 존재하지만, `bS95Q2` capture는 `tcp_handshake_only=101`, `tcp_handshake_follow_up=0`으로 끝난다. 따라서 Java discovery roster failure의 direct blocker는 “follow-up phase가 구현되지 않음”이 아니라, current discovery path가 아직 `internal:tcp/handshake` 단계에서 one-shot hold-open policy로 종료되도록 짜여 있다는 점이다.
- 2026-05-05: 하지만 `main.rs`에서 discovery-related `hold_transport_channel_open(..., false, ...)`를 `true`로 올린 fresh probe `/tmp/java-rust-mixed-membership.QlitPD`도 `tcp_handshake_count=96`, `tcp_handshake_follow_up=0`, `open_response=0`, `open_failure=132`, `handshake_timeout=95`, `added_rust=0`으로 남았다. 즉 current blocker는 Rust one-shot hold-open boolean alone이 아니라, Java discovery가 TCP handshake 이후 post-TCP `internal:transport/handshake`/`request_peers` phase로 아예 들어가지 못하는 sequencing 문제다.
- 2026-05-05: source `/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TransportHandshaker.java`를 same run `/tmp/java-rust-mixed-membership.QlitPD`와 맞추면, Java 쪽 high-level handshake path는 존재하고 timeout도 실제로 스케줄된다. actual stdout도 `channels_connected_on_response=96`, `handshake_timeout=95`를 보이지만 Rust capture의 `observed_transport_handshake_follow_up=0`이다. 따라서 current stop point는 “Java가 high-level handshake branch로 안 들어감”이 아니라 `handshakeRequestSender.sendRequest(...)`의 wire-send/observe boundary다. 남은 질문은 이 request가 실제로 안 나가는지, 아니면 Rust capture/parser가 현재 framing variant를 못 보는지다.
- 2026-05-05: `TransportHandshaker.sendHandshake(...)`에 `before_send_request/after_send_request/send_request_exception` marker를 추가하고 `TransportHandshaker.class`를 overlay한 fresh probe `/tmp/java-rust-mixed-membership.SyqdFH`를 actual로 돌린 결과, `before_send_request=37`, `after_send_request=37`, `send_request_exception=0`인데 same run의 Rust capture `observed_transport_handshake_follow_up=0`이었다. 즉 current stop point는 `sendRequest(...)` call entry가 아니라 `sendRequest` return 이후 actual wire write / Rust parser observe boundary다.
- 2026-05-05: `NativeOutboundHandler.sendMessage(...)`와 `OutboundHandler.sendBytes(...)`에 `before_send_bytes/after_send_bytes`, `before_channel_send/after_channel_send` marker를 넣고 overlay한 fresh probe `/tmp/java-rust-mixed-membership.9lByI5`를 actual로 돌리면 `before_send_request=37`, `after_send_request=37`, `before_send_bytes=38`, `after_send_bytes=38`, `before_channel_send=38`, `after_channel_send=38`, `send_request_exception=0`인데 Rust capture의 `observed_transport_handshake_follow_up=0`은 그대로다. 따라서 current stop point는 Java send/submit path 바깥, 즉 actual wire emission completion 또는 Rust capture/parser observe boundary다.
- 2026-05-05: `Netty4TcpChannel.sendMessage(...)`와 `ChannelPromise` completion marker까지 넣고 overlay한 fresh probe `/tmp/java-rust-mixed-membership.Byb43p`를 actual로 돌리면 `before_write_and_flush=38`, `after_write_and_flush=38`, `write_promise_success=41`, `write_promise_failure=1`이 찍힌다. 즉 Java Netty write completion success는 실제로 존재한다. 그럼에도 Rust capture `observed_transport_handshake_follow_up=0`은 그대로이므로, current direct blocker는 Java write-completion 이전이 아니라 handshake request의 raw bytes shape 자체 또는 Rust capture/parser observe 경계다.
- 2026-05-05: fresh probe `/tmp/java-rust-mixed-membership.jKjDLd`의 outbound marker를 actual로 보면 `steelsearch_native_outbound_stage=send_request_meta action=internal:tcp/handshake`와 `before_channel_send ... bytesLength=55 prefixHex=455300000031...`가 찍힌다. same run Rust capture는 action hint `internal:tcp/handshake`와 matching prefix를 남긴다. 또 source상 `TransportHandshaker.HANDSHAKE_ACTION_NAME`는 `internal:tcp/handshake`, `TransportService.HANDSHAKE_ACTION_NAME`는 별도 `internal:transport/handshake`다. 따라서 current blocker는 raw bytes parser miss가 아니라 Java discovery가 low-level `internal:tcp/handshake` 단계에서만 반복되고 high-level `internal:transport/handshake`/`request_peers` phase로 승격되지 못하는 점이다.
- 2026-05-05: source를 더 맞춰 보면 `HandshakingTransportAddressConnector`의 high-level `transportService.handshake(...)`는 `steelsearch_open_connection_stage=response` callback 안에서만 시작되고, `TcpTransport`는 그보다 앞에서 `executeHandshake(...)` 성공을 기다린다. actual run `/tmp/java-rust-mixed-membership.jKjDLd`도 `channels_connected_on_response=37`, `open_response=0`, `start_high_level_handshake=0`, `transport_handshake_send_meta=0`, `tcp_handshake_send_meta=37`이므로 current stop point는 high-level phase가 아니라 low-level `internal:tcp/handshake` completion 경계다. 남은 질문은 Rust가 응답한 low-level tcp handshake가 왜 Java `executeHandshake` success로 이어지지 않는가다.
- 2026-05-05: fresh probe `/tmp/java-rust-mixed-membership.b97g38`에서 Java `Netty4TcpChannel.write_promise_success` marker에 `local=`/`remote=`를 붙여 socket association을 actual로 대조했다. `check_handshake_socket_association_matches_rust_peers.py` 결과는 Java write-success local port 37개와 Rust `internal:tcp/handshake` peer port 37개가 36개 직접 overlap이며, lone mismatch는 Java `50066` vs Rust `54808` 한 쌍뿐이다. 즉 discovery low-level handshake write는 대체로 Rust capture가 본 same client sockets와 직접 매칭되므로, current blocker를 “Java가 write 후 다른 sibling socket을 timeout한다”로 보는 건 약하다. 다음 direct split은 same associated socket에서 Rust response bytes가 Java read-side lifecycle(`channelInactive`/close ordering, half-close, decoder entry 이전 event ordering)에서 왜 사라지는지다.
- 2026-05-05: `Netty4MessageChannelHandler`에 `channel_read local=...`, `channel_inactive local=...`, `exception_caught local=...` marker를 추가하고 fresh probe `/tmp/java-rust-mixed-membership.wOrV4z`를 actual로 돌렸다. `check_same_socket_read_lifecycle_closes_before_decoder.py` 결과는 low-level handshake write ports `37`, same-socket `channel_read overlap = 0`, `channel_inactive overlap = 0`, `exception overlap = 0`이다. stdout에 실제로 찍힌 `channel_read/channel_inactive` 1건은 unrelated socket `local=54735 remote=56246`뿐이었다. 즉 discovery handshake sockets는 `Netty4MessageChannelHandler` read/inactive/exception lifecycle까지도 아예 도달하지 못한다. current stop point는 message-handler lifecycle보다 더 앞, 즉 `Netty4TcpChannel` closeFuture 또는 lower Netty pipeline/event-loop close boundary 쪽이다.
- 2026-05-05: `Netty4TcpChannel`에 `close_future_listener`와 `close_trace_emit` marker를 추가하고 fresh probe `/tmp/java-rust-mixed-membership.t8348g`를 actual로 돌렸다. `check_same_socket_close_future_before_message_handler.py` 결과는 `write_ports=37`, `write_close_future_overlap=37`, `write_close_trace_overlap=37`, `write_read_overlap=0`, `write_inactive_overlap=0`이다. 즉 discovery handshake sockets는 message-handler read-side event 전에 전부 `Netty4TcpChannel.closeFuture`로 먼저 surface된다. 다만 close trace hint는 `unknown`과 `explicitLocalClose`가 섞여 있고 marker 시점에는 `local=null`이므로, 다음 direct split은 current close origin이 explicit local teardown인지, lower Netty pipeline/remote-side teardown인데 hint가 늦게/불완전하게 기록되는지다.
- 2026-05-05: same stdout `/tmp/java-rust-mixed-membership.t8348g/opensearch/stdout.log`를 low-level handshake write ports 기준으로만 다시 집계하면 `check_low_level_handshake_close_origin_is_explicit_local.py` 결과가 `write_ports=37`, `matched_ports=37`, `hint_counts={'explicitLocalClose': 37}`다. 즉 current discovery handshake sockets의 close origin은 mixed `unknown`이 아니라 전부 Java-side `Netty4TcpChannel.close()`에서 기록된 `explicitLocalClose`다. 남은 질문은 “무엇이 low-level tcp handshake success 이전에 이 explicit local close를 호출하는가”다.
- 2026-05-05: `Netty4TcpChannel.close()`에 stdout caller marker를 추가하고 fresh probe `/tmp/java-rust-mixed-membership.dKCQ3c`를 actual로 돌렸다. `check_low_level_handshake_close_caller.py` 결과는 `write_ports=37`, `matched_ports=37`, `caller_fingerprints=1`이며 sole fingerprint는 `IOUtils.close:89 -> IOUtils.close:131 -> IOUtils.close:114 -> CloseableChannel.closeChannels:107`다. 즉 low-level handshake sockets를 닫는 explicit local close direct caller는 single path `CloseableChannel.closeChannels`까지는 고정됐다. 남은 질문은 그보다 한 단계 위 upstream callback이 current same-run에서도 `TcpTransport.NodeChannels.close()` / `ChannelsConnectedListener.onResponse`인지다.
- 2026-05-05: `Netty4TcpChannel.close()` marker를 더 확장하고 fresh probe `/tmp/java-rust-mixed-membership.DHbkLb`를 actual로 돌렸다. `check_low_level_handshake_upstream_close_callback.py` 결과는 `write_ports=37`, `matched_ports=37`, `upstream_fingerprints=1`이며 sole chain은 `IOUtils.close -> CloseableChannel.closeChannels -> TcpTransport$ChannelsConnectedListener#closeAndFail:1193 -> TcpTransport$ChannelsConnectedListener#lambda$onResponse$2:1157 -> ActionListener$1#onFailure:90 -> TransportHandshaker$HandshakeResponseHandler#handleLocalException:184`다. 즉 current same-run discovery handshake socket close upstream callback은 `NodeChannels.close` fanout이 아니라 `HandshakeResponseHandler.handleLocalException`으로 귀결되는 `closeAndFail` path다. 남은 질문은 Rust low-level handshake response bytes가 실제로 write/flush되고 raw shape도 맞는데, 왜 Java는 `handleResponse`가 아니라 이 local exception/timeout ordering으로 수렴하는가다.
- 2026-05-05: same run `/tmp/java-rust-mixed-membership.DHbkLb/opensearch/stdout.log`를 handshaker marker와 같이 다시 집계하면 `before_send_request=37`, `after_send_request=37`, `response_read=0`, `handle_response=0`, `handle_exception=0`, `handle_local_exception=0`, `remove_handler=74`, `handshake_timeout=37`이다. 그런데 close stack fingerprint는 여전히 `TransportHandshaker$HandshakeResponseHandler#handleLocalException:184`를 포함한다. 즉 timeout callback이 먼저 `removeHandlerForHandshake()`를 호출해 pending handshake를 제거하고, 그 뒤 `closeAndFail` close callback이 `handleLocalException` stack으로 들어와도 `removeHandlerForHandshake(...) == null`이 되어 marker body를 실행하지 못하는 removal-order race가 current same-run behavior다. 남은 질문은 왜 Rust low-level handshake response bytes가 실제 wire에 있음에도 Java inbound 쪽에서 이 response가 pending handler removal 이전에 parser/dispatch로 들어오지 못하느냐다.
- 2026-05-05: same artifact `/tmp/java-rust-mixed-membership.DHbkLb`를 더 묶으면 direct boundary도 고정된다. `check_response_flush_stops_before_java_channel_read.py` 결과는 Rust `before_write/after_write/after_flush = 38/38/38`, capture `response_frame = 38`, Java same-socket `channelRead overlap = 0`, `response_read=0`, `handle_response=0`, `handshake_timeout=37`이다. 즉 low-level tcp handshake response bytes는 Rust에서 flush되고 capture에도 남지만, Java에서는 pending handler removal 이전은커녕 same-socket `Netty4MessageChannelHandler.channelRead`에도 도달하지 못한다. current direct boundary는 parser body가 아니라 그보다 앞선 Java lower inbound transport delivery 경계다.
- 2026-05-05: same capture `/tmp/java-rust-mixed-membership.DHbkLb/steelsearch/data/transport-seed-capture.json`의 `response_frame_sent_at_ms -> connection_end_at_ms`를 actual로 집계하면 low-level tcp handshake response `38건`의 median delta가 `973ms`다. same stdout은 `handshake_timeout=37`, same-socket `channelRead overlap = 0`, `explicitLocalClose`가 timeout count 이상이다. 즉 response bytes는 wire 위에서 즉시 사라지는 게 아니라 거의 `1s` 동안 socket에 남아 있다가 Java timeout local close로 끝난다. current direct boundary는 parser나 raw wire mismatch가 아니라 Java lower inbound NIO/Netty read wakeup 경계다.
- 2026-05-05: Netty bytecode `io.netty.channel.nio.AbstractNioByteChannel$NioByteUnsafe.read()`를 확인하면 read loop는 `AbstractNioByteChannel.doReadBytes(...)` 직후 바로 `ChannelPipeline.fireChannelRead(...)`와 `fireChannelReadComplete()`를 호출한다. same artifact `/tmp/java-rust-mixed-membership.DHbkLb/opensearch/stdout.log`는 same-socket `channelRead overlap = 0`, `handshake_timeout=37`, `close_future >= 37`이다. 따라서 current source+actual boundary는 OpenSearch parser 내부가 아니라 `NioByteUnsafe.read()`가 same socket bytes를 읽어 `fireChannelRead`까지 올리기 전, 즉 Netty selector/read-loop wakeup 경계다.
- 2026-05-05: Netty source contract을 더 보면 `DefaultChannelConfig` constructor는 `autoRead=1(true)`를 기본값으로 두고, `AbstractNioChannel.doBeginRead()`는 `readPending=true` 후 `addAndSubmit(readOps)`를 호출한다. 반면 `AbstractNioByteChannel.shouldBreakReadReady()`는 `isInputShutdown0` 또는 half-closure 조건만 검사한다. 따라서 current low-level handshake socket에서 `autoRead=false`나 ordinary `removeReadOp`가 선행 gating일 가능성은 낮고, source contract상 가장 직접적인 남은 후보는 selector-ready/read wakeup이 same socket에 대해 아예 오지 않거나, selector-ready 직후 `doReadBytes` 이전에 더 낮은 close path가 개입하는 경우다.
- 2026-05-05: `AbstractNioByteChannel$NioByteUnsafe.read()` bytecode를 더 보면 early return은 `shouldBreakReadReady()==true`일 때 `clearReadPending()` 후 return하는 branch뿐이고, 그 외에는 곧바로 `doReadBytes(...) -> fireChannelRead(...) -> fireChannelReadComplete()`로 간다. same artifact `/tmp/java-rust-mixed-membership.DHbkLb/opensearch/stdout.log`는 same-socket `channelRead overlap = 0`, `closeFuture >= write_ports`다. 따라서 current evidence는 “selector-ready는 왔지만 `doReadBytes` 직전 다른 close path가 개입했다”보다 “selector-ready/read wakeup 자체가 same socket에 대해 오지 않았다” 쪽으로 더 강하게 기운다.
- 2026-05-05: `AbstractNioChannel` contract까지 보면 constructor는 `SelectableChannel.configureBlocking(false)`를 수행하고, `doBeginRead()`는 valid `registration`에서 `readPending=true` 후 `addAndSubmit(readOps)`를 호출한다. same artifact `/tmp/java-rust-mixed-membership.DHbkLb/opensearch/stdout.log`는 same-socket `channelRead overlap = 0`, `handshake_timeout=37`이다. 따라서 current missing signal은 Netty registration/read-interest setup omission보다 더 아래, JDK selector-ready visibility 쪽으로 보는 편이 맞다.
- 2026-05-05: JDK `sun.nio.ch.SocketChannelImpl.translateReadyOps(...)` bytecode를 보면 `POLLIN`은 connected socket의 read ready로 올리고, `POLLERR | POLLHUP`도 current interest ops를 `nioReadyOps`로 write-back한다. 또 `translateInterestOps(...)`는 read interest를 `POLLIN`으로 변환한다. 따라서 current missing signal은 Java-side readiness translation omission보다 더 아래, selector poll/native readiness delivery 쪽으로 보는 편이 맞다.
- 2026-05-05: `libnio.so` symbol table을 다시 보면 selector branch는 이미 `Java_sun_nio_ch_Net_poll`, `Java_sun_nio_ch_PollSelectorImpl_poll`, 그리고 libc `epoll_wait`/`poll` 연계까지 내려왔다. 반면 current session은 여전히 `strace` 부재와 `perf raw_syscalls` 미지원 때문에 그 아래 native selector poll wakeup을 actual로 관측할 수 없다. 따라서 selector/native poll branch는 이 세션에서 practical stop point로 정리하는 편이 맞다.
- 2026-05-05: practical stop point를 메모만 하지 않고 checker로도 고정했다. `check_selector_branch_practical_stop_and_backlog_pivot.py`는 `Net_poll`, `PollSelectorImpl_poll`, `epoll_wait/poll` 경계와 `perf raw_syscalls` 미지원 상태를 다시 확인했고, selector/native poll branch는 현 세션에서 더 내려갈 생산성이 낮다고 정리했다. 따라서 다음 본류는 이 결론을 보존한 채 higher-level reproduction/workaround backlog, 특히 minimal standalone Java NIO/Netty client reproducer 쪽으로 pivot하는 편이 맞다.
- 2026-05-05: higher-level pivot 첫 단계로 `tools/MinimalSelectorHandshakeClient.java`를 추가했다. 이 client는 non-blocking `SocketChannel` + `Selector`로 `OP_CONNECT/OP_WRITE/OP_READ`를 직접 돌면서 request hex를 보내고 `read_ready`, `bytes_read`, `response_hex`를 JSON으로 출력한다. 따라서 다음 직접 확인은 이 standalone client를 fresh live Rust listener에 붙였을 때도 OpenSearch full stack과 같은 selector starvation이 재현되는지다.
- 2026-05-05: fresh live probe `/tmp/java-rust-mixed-membership.MwTgHe`의 Rust listener `127.0.0.1:59079`에 `MinimalSelectorHandshakeClient`를 실제로 붙여 보니 `connect_ready=true`, `write_ready=true`, `read_ready=true`, `bytes_written=55`, `bytes_read=29`, `response_hex=45530000001700000000000000010908216b1300000002000093b1bb41`, `duration_ms=33`이 나왔다. 즉 same low-level handshake starvation은 bare Java selector client에서는 재현되지 않는다. 남은 직접 질문은 이 차이가 OpenSearch full stack 특이점인지, 아니면 보다 작은 Netty integration 레벨에서도 재현되는지다.
- 2026-05-05: 그 다음 단계로 `tools/MinimalNettyHandshakeClient.java`도 추가하고 fresh live probe `/tmp/java-rust-mixed-membership.bvr0V8`의 Rust listener `127.0.0.1:51859`에 실제로 붙였다. 결과는 `connect_finished=true`, `channel_active=true`, `write_submitted=true`, `write_success=true`, `read_observed=true`, `bytes_written=55`, `bytes_read=29`, `response_hex=45530000001700000000000000010908216b1300000002000093b1bb41`였다. 즉 same low-level handshake starvation은 standalone Netty client에서도 재현되지 않는다. 남은 직접 질문은 generic selector/Netty가 아니라 OpenSearch transport/discovery stack의 어느 최소 차이가 same-socket read starvation을 만들고 있는지다.
- 2026-05-05: 더 가까운 stripped-down reproducer로 `tools/MinimalConcurrentNettyHandshakeClient.java`를 추가해 fresh live probe `/tmp/java-rust-mixed-membership.VXUxh6`의 Rust listener `127.0.0.1:46397`에 `37`개 low-level handshake를 동시 다발로 열고 각 channel에 `1s timeout -> explicit local close`를 걸었다. 결과는 `connect_finished=37`, `channel_active=37`, `write_submitted=37`, `write_success=37`, `read_observed=37`, `timeout_close=0`, `exception_count=0`이었다. 즉 OpenSearch discovery와 닮은 generic Netty concurrency/timeout 조건에서도 starvation은 재현되지 않는다. 남은 직접 질문은 OpenSearch-only 단계, 특히 `TcpTransport.executeHandshake` 주변의 transport channel wrapper, handshake handler registration/removal, `NodeChannels/connection profile` 경로 중 어떤 최소 차이가 same-socket read starvation을 만드는지다.
- 2026-05-05: OpenSearch-only workaround hypothesis로 `TcpTransport.executeHandshake(...)`의 low-level handshake timeout을 `1s` 대신 최소 `5s`로 override하고 marker `steelsearch_tcp_open_stage=execute_handshake_timeout_override`를 추가했다. helper overlay에도 `org/opensearch/transport/TcpTransport.class`를 넣은 뒤 fresh probe `/tmp/java-rust-mixed-membership.BI688f`를 돌리면 marker는 실제로 `9회` 찍혔고 `handshake_timeout[5s]=8`, `handshake_timeout[1s]=0`으로 바뀌었다. 하지만 같은 run에서 `response_read=0`, `handle_response=0`, `open_response=0`, `open_failure=42`는 그대로였다. 즉 current issue는 “1초 timeout이 너무 짧다”는 가설이 아니라, timeout을 늘려도 inbound response parse 자체가 열리지 않는 OpenSearch-only 경로 쪽이다.
- 2026-05-05: tiny OpenSearch-side harness로 `tools/org/opensearch/transport/MinimalTransportHandshakerHarness.java`를 추가했다. 이 harness는 same package에서 `TransportHandshaker`를 직접 instantiate하고, plain socket으로 받은 Rust low-level handshake response를 `removeHandlerForHandshake(requestId) -> handler.read(...) -> handler.handleResponse(...)`에 직접 넘긴다. fresh live probe `/tmp/java-rust-mixed-membership.25aaMS`의 Rust listener `127.0.0.1:36471`에 붙인 결과 `steelsearch_transport_handshaker_stage=response_read`, `handle_response`가 실제로 즉시 발생했고 harness `dispatch_success=true`였다. 즉 `TransportHandshaker` callback path 자체는 bytes만 전달되면 바로 열린다. 다만 현재 harness는 full transport body를 곧바로 `HandshakeResponse.read()`에 넣는 framing shortcut 때문에 version parse가 `0.0.0-alpha0`로 어긋나 `IllegalStateException(unsupported version)`으로 끝난다. 따라서 남은 직접 질문은 handshaker path가 아니라, payload-accurate strip/decode를 넣어도 same conclusion이 유지되는지다.
- 2026-05-05: `MinimalTransportHandshakerHarness`에 `lowLevelResponsePayload(...)`를 추가해 low-level response frame에서 `requestId/status/headerVersion/variableHeaderSize/variableHeaderBytes`를 건너뛴 payload만 `HandshakeResponse.read()`에 전달하도록 고쳤다. fresh live probe `/tmp/java-rust-mixed-membership.diWCrF`의 Rust listener `127.0.0.1:50705`에 다시 붙인 결과 `response_read`, `handle_response` marker가 실제로 발생했고 harness JSON도 `dispatch_success=true`, `response_parsed=true`, `response_version=3.7.0`, `result=response`로 정상화됐다. 즉 low-level response payload shape와 `TransportHandshaker` parser 자체는 문제가 아니다. 남은 직접 질문은 manual dispatch를 빼고 OpenSearch full stack과 같은 inbound response delivery/dispatch(`Netty4MessageChannelHandler`/`InboundPipeline`/`NativeMessageHandler`)를 한 단계씩 다시 넣으면 어느 지점에서 starvation이 처음 생기느냐다.
- 2026-05-05: 그 다음 단계로 `tools/org/opensearch/transport/MinimalInboundPipelineHarness.java`를 추가해 plain socket으로 읽은 low-level tcp handshake response frame `29 bytes`를 `ReleasableBytesReference`로 감싸 `InboundPipeline.handleBytes(...)`에 직접 넣었다. fresh live probe `/tmp/java-rust-mixed-membership.oSzVqm`의 Rust listener `127.0.0.1:44335`에 붙인 결과 `steelsearch_inbound_pipeline_stage=handle_bytes remote=/127.0.0.1:44335 length=29`가 찍혔고 harness JSON은 `message_received=true`, `header_is_handshake=true`, `header_is_response=true`, `request_id=1`, `header_version=2.19.0`, `content_length=4`였다. 즉 raw low-level response frame은 `InboundPipeline` decode/aggregate 단계까지는 정상 복구된다. 남은 직접 질문은 그 다음 단계인 `NativeMessageHandler.messageReceived(...)`에서 `handshaker.removeHandlerForHandshake()/handleResponse`까지도 정상적으로 이어지는지, 아니면 거기서 처음 어긋나는지다.
- 2026-05-05: 이어서 `tools/org/opensearch/transport/MinimalNativeMessageHandlerHarness.java`를 추가했다. 이 harness는 `TransportHandshaker.sendHandshake(...)`의 sender는 plain socket write만 수행하게 두고, raw response frame은 `InboundPipeline.handleBytes(...)`로 복구한 뒤 recovered `InboundMessage`를 `NativeMessageHandler.messageReceived(...)`에 직접 넘긴다. fresh live probe `/tmp/java-rust-mixed-membership.5NRfda`의 Rust listener `127.0.0.1:44259`에 붙인 결과 `steelsearch_native_message_stage=handshake_response_header`, `...handler_lookup handlerMissing=false`, `...handshake_response_dispatch`, 그리고 `steelsearch_transport_handshaker_stage=response_read`, `handle_response`가 모두 실제로 발생했고 harness JSON도 `result=response`, `response_version=3.7.0`이었다. 즉 tiny harness 안에서는 `InboundPipeline -> NativeMessageHandler -> TransportHandshaker.handleResponse`까지 전부 정상이다. 남은 직접 질문은 plain-socket-fed harness와 full OpenSearch Netty socket delivery 사이의 차이, 즉 `Netty4MessageChannelHandler`/event-loop/channelRead delivery가 어디서 current starvation을 만들고 있는지다.
- 2026-05-05: 그 다음 단계로 `tools/org/opensearch/transport/MinimalChannelReadDispatchHarness.java`를 추가했다. 이 harness는 plain socket으로 읽은 response frame을 `EmbeddedChannel.writeInbound(Unpooled.wrappedBuffer(frame))`로 넣고, custom `channelRead(...)` body에서 raw `ByteBuf`를 `ReleasableBytesReference`로 바꿔 `InboundPipeline -> NativeMessageHandler -> TransportHandshaker` 체인에 전달한다. fresh live probe `/tmp/java-rust-mixed-membership.72hNeg`의 Rust listener `127.0.0.1:45403`에 붙인 결과 `channel_read_triggered=true`, `steelsearch_inbound_pipeline_stage=handle_bytes`, `steelsearch_native_message_stage=handshake_response_header/dispatch`, `steelsearch_transport_handshaker_stage=response_read/handle_response`가 모두 실제로 발생했고 harness JSON도 `result=response`, `response_version=3.7.0`이었다. 즉 `ByteBuf -> channelRead -> InboundPipeline -> NativeMessageHandler -> TransportHandshaker.handleResponse`까지 tiny harness에서는 정상이다. 남은 직접 질문은 actual Netty socket/event-loop read delivery, 즉 selector wakeup과 real `NioSocketChannel` read 경계에서만 current starvation이 생기는지다.
- 2026-05-05: 마지막 차이를 더 줄이기 위해 `tools/org/opensearch/transport/MinimalNettySocketDispatchHarness.java`를 추가했다. 이 harness는 real Netty `Bootstrap`/`NioEventLoopGroup`/`NioSocketChannel`을 열고, `channelActive`에서 `TransportHandshaker.sendHandshake(...)`를 호출한 뒤 real `channelRead`에서 받은 `ByteBuf`를 `InboundPipeline -> NativeMessageHandler -> TransportHandshaker` 체인으로 넘긴다. stale listener attach는 `Connection refused`였지만, keepalive live probe(`/tmp/java-rust-mixed-membership-live-nettysocket.handoff.json`)를 띄운 same run에서 rust listener `127.0.0.1:48839`에 붙인 결과 `steelsearch_transport_handshaker_stage=before/after_send_request`, `steelsearch_inbound_pipeline_stage=handle_bytes`, `steelsearch_native_message_stage=handshake_response_header/dispatch`, `steelsearch_transport_handshaker_stage=response_read/handle_response`가 모두 실제로 발생했고 harness JSON도 `channel_active=true`, `channel_read_triggered=true`, `result=response`, `response_version=3.7.0`이었다. 따라서 current starvation은 generic selector/Netty socket delivery가 아니라 full OpenSearch stack 안의 추가 단계, 특히 `TcpTransport.executeHandshake` 주변 pending-handler lifecycle/timeout/close wiring 쪽으로 더 좁혀진다.
- 2026-05-06: 그 pending-handler lifecycle을 직접 찌르기 위해 `tools/org/opensearch/transport/MinimalDelayedNettySocketDispatchHarness.java`를 추가했다. 이 harness는 real Netty socket delivery는 그대로 두고, `channelRead`에서 받은 response bytes의 actual dispatch만 의도적으로 `dispatch_delay_ms=1500`으로 미뤄 `timeout_ms=1000` 뒤에 `InboundPipeline -> NativeMessageHandler -> TransportHandshaker` 체인으로 넣는다. keepalive live probe(`/tmp/java-rust-mixed-membership-live-delayed-netty.handoff.json`)의 rust listener `127.0.0.1:57155`에 same-run attach한 결과 stdout에는 `steelsearch_transport_handshaker_stage=remove_handler`, `handle_local_exception requestId=1 causeClass=org.opensearch.transport.ConnectTransportException causeMessage= handshake_timeout[1s]`, 이어서 늦게 `steelsearch_inbound_pipeline_stage=handle_bytes ... length=29`, `steelsearch_native_message_stage=handshake_response_header`, `handshake_response_handler_lookup requestId=1 handlerMissing=true`가 실제로 찍혔다. harness JSON도 `channel_active=true`, `channel_read_triggered=true`, `delayed_dispatch_triggered=true`, `result=failure`, `failure_class=org.opensearch.transport.ConnectTransportException`였다. 즉 full stack에서 본 현상은 “response bytes shape 문제”가 아니라 OpenSearch-side `handshake_timeout -> removeHandlerForHandshake -> late dispatch handlerMissing` race만으로도 충분히 재현된다.
- 2026-05-06: 그 다음 workaround hypothesis로 `TransportHandshaker.sendHandshake(...)`에 `STEELSEARCH_TIMEOUT_GRACE=1500ms`를 넣어 timeout 시 즉시 `handleLocalException/removeHandlerForHandshake`로 가지 않고 grace window 뒤에만 fail 하도록 바꿨다. compile 후 fresh probe `/tmp/java-rust-mixed-membership.EXOhyg`를 actual로 돌리면 `steelsearch_transport_handshaker_stage=timeout_grace_start`와 `timeout_grace_expire`는 각각 `19회` 실제로 찍히고 `handshake_timeout[5s]=19`로 timeout 시점도 미뤄진다. 하지만 같은 run에서 `response_read=0`, `handle_response=0`, `open_response=0`, `handlerMissing=false/true=0`은 그대로였다. 즉 full OpenSearch path starvation은 “timeout 시 pending handler를 너무 빨리 제거한다”는 단독 가설만으로는 설명되지 않고, 그 이후 `ChannelsConnectedListener.closeAndFail -> CloseableChannel.closeChannels` local teardown 또는 더 낮은 inbound delivery 경계가 함께 작동하는 쪽으로 봐야 한다.
- 2026-05-06: 그 local teardown hypothesis를 actual로 보려고 `TcpTransport$ChannelsConnectedListener.closeAndFail(...)`에 handshake-timeout 전용 `STEELSEARCH_CLOSE_AND_FAIL_GRACE=1500ms` delay-close branch를 넣고 fresh probe `/tmp/java-rust-mixed-membership.PTXGLs`를 돌렸다. 결과는 `timeout_grace_start=19`, `timeout_grace_expire=19`, `handshake_timeout[5s]=19`였지만 `close_and_fail_delay_close=0`, `close_and_fail_delay_close_expire=0`, `response_read=0`, `handle_response=0`, `open_response=0`이었다. 같은 stdout를 직접 보면 local teardown 로그의 대부분은 `channels_connected_listener_onFailure ... causeMessage=Connection refused`와 `open_connection_stage=failure ... connect_exception` 경로에서 먼저 발생하고, `handshake_timeout[5s]`는 더 바깥 `open_connection_stage=failure`에만 찍힌다. 따라서 이번 patch는 “close를 늦춰도 안 된다”라기보다, current timeout failure socket을 실제로 닫는 boundary가 `closeAndFail`의 이 branch가 아니라 더 다른 upstream callback/exception object라는 뜻이다.
- 2026-05-06: 그 upstream object를 actual로 고정하려고 `HandshakingTransportAddressConnector.openConnection(...).onFailure(...)` marker를 `causeCauseClass/causeCauseMessage/topFrame`까지 확장했다. fresh probe `/tmp/java-rust-mixed-membership.nfc1yu`에서 `connect_exception` failures는 `causeCauseClass=io.netty.channel.AbstractChannel$AnnotatedConnectException`, `topFrame=org.opensearch.transport.TcpTransport$ChannelsConnectedListener.onFailure(TcpTransport.java:1180)`로 들어왔다. 반면 `handshake_timeout[5s]` failures는 `causeCauseClass=null`, `topFrame=org.opensearch.transport.TransportHandshaker.lambda$sendHandshake$1(TransportHandshaker.java:117)`로 직접 올라왔다. 즉 current timeout failure object는 `closeAndFail` 안에서 다시 만들어지는 게 아니라 `TransportHandshaker` timeout callback에서 바로 생성되어 connector failure로 전파된다. 따라서 timeout-local-teardown workaround를 걸어야 하는 진짜 boundary는 `closeAndFail` message filter가 아니라 `executeHandshake(..., e -> closeAndFail(...))` failure callback 또는 `TransportHandshaker` timeout callback 자체다.
- 2026-05-06: 그 가설을 actual로 확인하려고 `TcpTransport$ChannelsConnectedListener.onResponse(...)` 안의 `executeHandshake(..., e -> closeAndFail(...))` failure callback에 직접 `execute_handshake_failure_grace_start/expire` marker와 grace-delay branch를 넣고 fresh probe `/tmp/java-rust-mixed-membership.sbxeSb`를 돌렸다. 결과는 `failure_grace_start=0`, `failure_grace_expire=0`, `response_read=0`, `handle_response=0`, `open_response=0`, `handshake_timeout[5s]=19`였다. 같은 run의 connector failure line은 여전히 `topFrame=org.opensearch.transport.TransportHandshaker.lambda$sendHandshake$1(TransportHandshaker.java:117)`를 가리켰다. 즉 current timeout failures는 `closeAndFail`뿐 아니라 `executeHandshake(..., e -> ...)` callback grace branch조차 실제로 타지 않고, `TransportHandshaker` timeout callback에서 connector failure로 바로 surface되고 있다. 남은 직접 질문은 full stack에서 이 callback을 우회하는 actual propagation path가 정확히 무엇이냐다.
- 2026-05-06: 위 두 actual 결과를 합치면 current propagation shape는 꽤 좁혀진다. `/tmp/java-rust-mixed-membership.nfc1yu`는 connector failure가 `topFrame=TransportHandshaker.lambda$sendHandshake$1`인 raw `ConnectTransportException(handshake_timeout[5s])`를 직접 받는다고 보여주고, `/tmp/java-rust-mixed-membership.sbxeSb`는 `executeHandshake(..., e -> closeAndFail(...))` failure callback에 건 grace marker가 `0회`라고 보여준다. 따라서 current full-stack starvation은 “callback 안에서 close를 너무 빨리 했다”보다, `TransportHandshaker` timeout failure가 우리가 기대한 `ChannelsConnectedListener` failure lambda를 실제로 거치지 않고 connector failure 쪽으로 바로 surface되는 propagation path가 있다는 뜻이다. 다음 직접 질문은 `TcpTransport.executeHandshake(...)`에 넘긴 listener wrapper가 실제로 호출되는지 여부다.
- 2026-05-06: 그 마지막 우회 가설을 닫기 위해 `TcpTransport.executeHandshake(...)`에 전달하는 listener 자체를 wrapper로 감싸 `execute_handshake_listener_onFailure/onResponse` marker를 넣었다. fresh probe `/tmp/java-rust-mixed-membership.PCeT7B`에서는 `execute_handshake_listener_onFailure=19`, `execute_handshake_listener_onResponse=0`, `response_read=0`, `handle_response=0`, `handshake_timeout[5s]=38`이었고, sample line은 `causeClass=org.opensearch.transport.ConnectTransportException causeMessage=[][127.0.0.1:45459] handshake_timeout[5s]`였다. 즉 current timeout failure는 `TransportHandshaker.lambda$sendHandshake$1`에서 생성될 뿐 아니라, `executeHandshake`에 넘긴 listener의 `onFailure(...)`까지는 실제로 도달한다. 따라서 더 이상 “listener 자체를 우회한다”가 아니라, 그 listener body 안에서 `response_read/open_response` 복구 없이 failure-only로 수렴하는 subsequent close/teardown ordering이 남은 직접 질문이다.
- 2026-05-06: 그 ordering을 보려고 `ChannelsConnectedListener.onResponse(...)` 안의 inner failure lambda에 `execute_handshake_failure_lambda_enter/timeout_branch/non_timeout_branch/close_and_fail_enter` marker를 넣고 compile와 probe를 직렬로 묶어 `/tmp/java-rust-mixed-membership.zcYAxd`를 actual로 돌렸다. 결과는 `execute_handshake_listener_onFailure=19`인데 inner lambda body marker는 전부 `0회`였다. 같은 run에서 wrapper marker가 찍힌다는 건 `TcpTransport.class` overlay는 실제로 타고 있다는 뜻인데, inner lambda body marker가 0인 건 그 lambda가 들어 있는 `TcpTransport$ChannelsConnectedListener.class`가 helper overlay에 포함되지 않았을 가능성이 가장 높다. 따라서 이 시점의 direct blocker는 ordering 자체보다 overlay coverage split이며, 다음 직접 작업은 `TcpTransport$ChannelsConnectedListener.class`를 overlay에 명시적으로 포함시켜 같은 marker set을 다시 돌리는 일이다.
- 2026-05-06: helper overlay에 `TcpTransport$ChannelsConnectedListener.class`를 실제로 추가한 뒤 같은 probe를 다시 돌린 `/tmp/java-rust-mixed-membership.OuF1eu`에서는 inner ordering marker가 복구됐다. 결과는 `execute_handshake_listener_onFailure=15`, `execute_handshake_failure_lambda_enter=15`, `execute_handshake_failure_timeout_branch=15`, `execute_handshake_failure_grace_start=15`, `execute_handshake_failure_grace_expire=14`, `close_and_fail_enter=48`, `response_read=0`, `handle_response=0`, `handshake_timeout[5s]=130`이었다. sample ordering도 `execute_handshake_failure_timeout_branch -> execute_handshake_failure_grace_expire -> close_and_fail_enter(handshake_timeout[5s])`로 실제 확인됐다. 따라서 current full-stack path는 timeout branch와 delayed `closeAndFail`를 실제로 타더라도 여전히 `response_read/open_response`를 복구하지 못한다. 남은 직접 질문은 “1.5초가 짧아서 못 읽는가”를 더 강한 grace window나 same-socket `channelRead` marker 재결합으로 배제하는 일이다.
- 2026-05-06: 그 stronger workaround hypothesis를 actual로 닫기 위해 `STEELSEARCH_TIMEOUT_GRACE`와 `STEELSEARCH_CLOSE_AND_FAIL_GRACE`를 `10s`까지 늘리고 직렬 compile+probe `/tmp/java-rust-mixed-membership.H87Ghe`를 다시 돌렸다. 결과는 `execute_handshake_listener_onFailure=8`, `execute_handshake_failure_lambda_enter=8`, `execute_handshake_failure_timeout_branch=8`, `execute_handshake_failure_grace_start=8`, `execute_handshake_failure_grace_expire=7`, `close_and_fail_enter=41`이었지만, 여전히 `response_read=0`, `handle_response=0`, `open_response=0`, `netty_channel_read=1`이었다. 즉 timeout branch와 delayed `closeAndFail`를 훨씬 오래 유지해도 OpenSearch full stack은 low-level response를 결국 읽어내지 못한다. 따라서 “늦지만 언젠가는 읽힌다” 가설은 사실상 닫혔고, 남은 직접 질문은 delayed timeout path의 same socket에 대해 `channelRead` delivery 자체가 정말 없는지 port-correlated actual로 다시 고정하는 일이다.
- 2026-05-06: 그 same-socket read delivery 부재를 actual로 고정하려고 checker `/home/ubuntu/steelsearch/tools/check_delayed_timeout_same_socket_no_channelread.py`를 추가하고 delayed timeout sample `/tmp/java-rust-mixed-membership.H87Ghe/opensearch/stdout.log`에 적용했다. 결과는 `timeout_ports=1`, `close_ports=1`, `read_local_ports=0`, `read_remote_ports=0`, `timeout_read_overlap=[]`, `close_read_overlap=[]`, `checker_result=delayed_timeout_same_socket_still_never_reaches_channelRead`였다. 따라서 delayed timeout path에서 even `10s` grace를 주더라도 same socket은 끝까지 `Netty4MessageChannelHandler.channelRead`에 들어오지 않는다. 이 higher-level branch는 사실상 practical stop point에 가까워졌고, 다음 선택지는 결론 문서화냐 추가 native/Netty event-loop instrumentation backlog냐의 정리다.
- 2026-05-06: 마지막으로 checker `/home/ubuntu/steelsearch/tools/check_full_opensearch_read_starvation_practical_stop.py`를 추가해 delayed-timeout full-stack artifact `/tmp/java-rust-mixed-membership.H87Ghe/opensearch/stdout.log`를 한 번 더 묶어 판정했다. 결과는 `timeout_branch=8`, `grace_expire=7`, `close_timeout=67`, `response_read=0`, `handle_response=0`, `channel_read=1`, `checker_result=full_opensearch_read_starvation_branch_is_at_practical_stop_point_and_backlog_pivot_is_reasonable`였다. 따라서 current full OpenSearch read-starvation branch는 practical stop point에 도달했다. 즉 higher-level conclusion은 충분히 고정됐고, 여기서 더 파는 것보다 broader backlog나 lower native/Netty instrumentation candidate로 pivot하는 편이 더 생산적이다.
- current baseline regression은 low-level handshake response emit timing 지연이 아니라 post-response lifecycle이 follow-up-capable mix에서 idle-timeout/keepalive-only로 바뀐 쪽과 더 잘 맞는다. next split은 `hold_transport_channel_open` 조건/keepalive scheduling/pre-first-frame timeout branch 중 무엇이 이 lifecycle shift를 만들었는지다.
- current source의 low-level tcp handshake no-followup path는 `hold_transport_channel_open(..., true, ...)`로 proactive keepalive를 켠다. current baseline idle-timeout sockets는 실제 keepalive=1인데, old formed artifact의 tcp idle-timeout sockets는 keepalive=0이다. next split은 이 source/runtime delta가 baseline regression의 직접 원인인지다.
- low-level tcp no-followup branch의 proactive keepalive를 꺼도 membership_timeout/follow_up_absent는 그대로였다. keepalive는 lifecycle shape를 remote_eof-only로 바꾸지만 direct fix는 아니다. next split은 old formed에서 실제로 관측된 `follow_up_received within 400ms` path다.
- old formed artifact의 400ms 내 follow-up은 모두 즉시 `internal:transport/handshake` promotion이었다. current tree는 low-level tcp handshake request만 반복하고 이 Java-side promotion path에는 전혀 못 들어간다. next split은 current Java source/runtime gate다.
- current source/runtime gate는 `TransportHandshaker.handleResponse -> executeHandshake listener.onResponse` chain이다. actual current run은 `response_read=0`, `handle_response=0`, `execute_handshake_listener_onResponse=0`이므로 이 gate가 전혀 안 열린다. next question은 이 unknown이 이미 practical stop으로 정리한 full OpenSearch read-starvation branch와 사실상 동일한지다.
- rust-primary/java-replica branch의 남은 direct unknown은 기존 full OpenSearch read-starvation practical stop과 사실상 동일하다. 따라서 next productive branch는 additional instrumentation보다 actual mixed-cluster evidence (`index/delete/update actual run`)다.
- `index/delete/update actual run`을 `live_handoff_ready` report로 바로 붙이면 `prepare` phase의 `DELETE /{index}`가 20s HTTP timeout으로 실패했다. 즉 actual CRUD run의 최소 ready gate는 단순 success_harness_handoff보다 더 강해야 한다.
- actual CRUD start gate는 이제 `prepare-ready.json`/phase artifact로 명시화됐다. 남은 일은 wrapper가 `live_handoff_ready`를 그대로 소비하지 않고 `membership_formed=true` 또는 동등한 stronger gate를 요구하게 만드는 것이다.
- wrapper는 이제 `membership_formed=true`가 아닌 probe report를 actual harness에 넘기지 않는다. 다음 blocker는 fresh formed live handoff producer 자체다.

## 2026-05-06 formed-only live handoff producer

- `probe_java_rust_mixed_membership.sh`는 이제 optional `JAVA_RUST_MIXED_MEMBERSHIP_FORMED_HANDOFF_REPORT_PATH`를 지원한다.
- 스크립트 시작 시 weak handoff path와 formed-only path를 둘 다 stale-cleanup 한다.
- weak `LIVE_HANDOFF_REPORT_PATH`는 기존처럼 early `live_handoff_ready` snapshot을 남긴다.
- formed-only path는 `membership_formed=true`가 실제로 성립한 경우에만 write한다.
- actual failure baseline(`/tmp/java-rust-mixed-membership.formed-only`)에서
  - weak handoff `/tmp/java-rust-mixed-membership.formed-only.live.json`는 생성됐고
  - `membership_formed=false`, `failure_stage=live_handoff_ready`, `observed_node_count=0`였다.
  - formed-only handoff `/tmp/java-rust-mixed-membership.formed-only.formed.json`는 생성되지 않았다.
- 따라서 producer 단계에서도 weak handoff와 formed handoff를 분리할 수 있게 됐고, current blocker는 fresh formed handoff producer 자체다.

## 2026-05-06 fresh formed-only handoff attempt

- best-known probe 조건(`STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS=5000`, split build, java forwarding validated)으로 fresh formed-only handoff를 다시 시도했다.
- workdir: `/tmp/java-rust-mixed-membership.formed-only-fresh`
- weak handoff `/tmp/java-rust-mixed-membership.formed-only-fresh.live.json`는 생성됐고
  - `membership_formed=false`
  - `failure_stage=live_handoff_ready`
  - `observed_node_count=0`
  이었다.
- formed-only handoff `/tmp/java-rust-mixed-membership.formed-only-fresh.formed.json`는 끝내 생성되지 않았다.
- 따라서 strengthened wrapper 아래 actual CRUD run으로 넘어가기 전 blocker는 여전히 wrapper가 아니라 fresh formed membership producer 자체다.

## 2026-05-06 fresh formed-only producer remote EOF delta

- checker `check_fresh_formed_only_producer_points_to_immediate_remote_eof.py`를 추가했다.
- old formed capture(`/tmp/java-rust-mixed-membership.3aSgG8/steelsearch/data/transport-seed-capture.json`)와 current fresh attempt(`/tmp/java-rust-mixed-membership.formed-only-fresh/steelsearch/data/transport-seed-capture.json`)를 비교하면:
  - old formed: `tcp_total=5`, `follow_up_count=2`, follow-up action은 모두 `internal:transport/handshake`
  - current fresh: `tcp_total=105`, `follow_up_count=0`, `remote_eof_count=105`, `idle_timeout_count=0`, `keepalive_total=0`
- 따라서 current fresh formed-only producer failure는 keepalive/idle-timeout보다는 `tcp handshake response` 직후 peer가 immediate `remote_eof`로 닫혀 follow-up promotion을 전혀 못 여는 쪽에 더 직접적으로 맞다.

## 2026-05-06 fresh formed-only producer close-path split

- checker `check_fresh_formed_only_remote_eof_vs_java_close.py`를 추가했다.
- current fresh run(`/tmp/java-rust-mixed-membership.formed-only-fresh`) 기준:
  - `remote_eof_port_count=105`
  - `explicit_local_close_port_count=104`
  - `remote_eof_explicit_overlap_count=104`
  - `remote_eof_unknown_overlap_count=0`
- 따라서 current fresh formed-only producer failure의 immediate `remote_eof`는 Rust hold-open lifecycle보다 Java same-socket `explicitLocalClose` path 쪽이 더 직접적이다.

## 2026-05-06 old follow-up vs current close fingerprint

- checker `check_fresh_formed_only_close_fingerprint_vs_old_followup.py`를 추가했다.
- old formed capture는 `old_follow_up_count=2`, follow-up action이 모두 `internal:transport/handshake`였다.
- current fresh run의 dominant close fingerprint는
  - `TcpTransport$ChannelsConnectedListener#closeAndFail <- lambda$onResponse$2 <- ActionListener$1#onFailure <- TcpTransport#lambda$executeHandshake$26` 104회
  - `TcpTransport$ChannelsConnectedListener#closeAndFail <- onFailure <- ActionListener#lambda$toBiConsumer$2 <- CompletableContext#lambda$addListener$0` 34회
  로 수렴했다.
- 따라서 current fresh producer regression은 old formed의 immediate transport-handshake promotion 대신 `executeHandshake onFailure -> closeAndFail -> explicitLocalClose` collapse로 보는 편이 맞다.

## 2026-05-06 divergence gate before handleResponse

- checker `check_fresh_formed_only_diverges_before_handle_response.py`를 추가했다.
- source상
  - `TransportHandshaker.java`는 `listener.onResponse` path를
  - `TcpTransport.java`는 `executeHandshake(...)` promotion path를
  유지한다.
- old formed capture는 `old_follow_up_count=2`였지만 current fresh stdout은
  - `response_read=0`
  - `handle_response=0`
  - `execute_handshake_listener_onResponse=0`
  - `execute_handshake_listener_onFailure=104`
  이었다.
- 따라서 current fresh formed-only producer regression의 direct divergence gate는 `TransportHandshaker.handleResponse` 이전이며, 이후 path는 timeout-driven `executeHandshake onFailure -> closeAndFail -> explicitLocalClose` collapse다.

## 2026-05-06 formed-only producer subtree practical stop

- checker `check_fresh_formed_only_matches_full_read_starvation_stop.py`를 추가했다.
- existing practical stop baseline(`/tmp/java-rust-mixed-membership.H87Ghe/opensearch/stdout.log`)의 `same-socket never reaches channelRead` 성질과 current fresh stdout(`/tmp/java-rust-mixed-membership.formed-only-fresh/opensearch/stdout.log`)를 비교하면
  - `response_read=0`
  - `handle_response=0`
  - `execute_handshake_listener_onFailure=104`
  - `handshake_timeout[1s]=520`
  - `explicit_local_close=125`
  이고 checker result는 `fresh_formed_only_regression_remaining_unknown_matches_existing_full_opensearch_read_starvation_practical_stop`였다.
- 따라서 formed-only producer subtree의 남은 unknown은 새 문제라기보다 기존 full OpenSearch read-starvation practical stop과 사실상 동일하다.

## 2026-05-06 next backlog after formed-only practical stop

- checker `check_next_backlog_after_formed_only_practical_stop.py`를 추가했다.
- actual CRUD prepare gate artifact(`/tmp/rust-primary-java-replica-readygate-direct/prepare-phase.json`)는
  - `prepare_ready_gate=false`
  - `prepare_ready_node_count=0`
  - `prepare_ready_error=TimeoutError: timed out`
  였다.
- formed-only subtree stop checker(`/tmp/formed-only-stop-check.txt`)는 `fresh_formed_only_regression_remaining_unknown_matches_existing_full_opensearch_read_starvation_practical_stop`였다.
- 따라서 next productive branch는 `bulk replay actual run`이 아니라 stronger formed producer restore candidate다.

## 2026-05-06 skip active probes candidate

- stronger formed producer restore candidate로 `JAVA_RUST_MIXED_MEMBERSHIP_SKIP_ACTIVE_STEELSEARCH_PROBES=1`를 actual probe했다.
- fresh run `/tmp/java-rust-mixed-membership.no-active-probes`는 weak handoff만 남기고 formed-only handoff를 만들지 못했다.
- checker `check_skip_active_probes_does_not_restore_formed_handoff.py` 결과:
  - baseline: `membership_formed=false`, `observed_node_count=0`, `follow_up_count=0`, `remote_eof_count=17`
  - no-active: `membership_formed=false`, `observed_node_count=0`, `follow_up_count=0`, `remote_eof_count=15`
  - checker result: `skipping_active_steelsearch_probes_does_not_restore_formed_handoff_or_followup`
- 따라서 active steelsearch probes perturbation 가설은 current restore candidate로 닫힌다.

## 2026-05-06 java-only initial_cluster_manager_nodes candidate

- stronger formed producer restore candidate로 `JAVA_RUST_MIXED_MEMBERSHIP_INITIAL_CLUSTER_MANAGER_NODES=java-primary-1`를 actual probe했다.
- fresh run `/tmp/java-rust-mixed-membership.java-only-icmn`은 formed-only handoff를 만들지 못했지만, weak report shape는 baseline보다 좁혀졌다:
  - `observed_node_count=0 -> 1`
  - `tcp_total=17 -> 1`
  - `remote_eof_count=17 -> 1`
- checker `check_java_only_icmn_candidate_narrows_but_does_not_restore.py` 결과는 `java_only_initial_cluster_manager_nodes_candidate_narrows_failure_shape_but_does_not_restore_formed_handoff`였다.
- 따라서 이 candidate는 formed handoff/follow-up을 복구하진 못했지만, next stronger candidate를 same 1-node observed state 위에서 고를 수 있게 failure shape를 더 좁혔다.

## 2026-05-06 java-only icmn + 15000ms candidate

- `JAVA_RUST_MIXED_MEMBERSHIP_INITIAL_CLUSTER_MANAGER_NODES=java-primary-1` narrowed state 위에 `STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS=15000`를 얹어 actual probe했다.
- live report `/tmp/java-rust-mixed-membership.java-only-icmn-15s.live.json`는 여전히
  - `membership_formed=false`
  - `observed_node_count=1`
  - `failure_stage=live_handoff_ready`
  였고 formed-only handoff는 생성되지 않았다.
- checker `check_java_only_icmn_15s_does_not_restore_followup.py` 결과도 java-only 5s와 15s가 둘 다 `tcp_total=1`, `follow_up_count=0`, `remote_eof_count=1`로 같았다.
- 따라서 same 1-node observed state에서는 pre-first-frame timeout을 `5000 -> 15000ms`로 늘려도 follow-up/formed handoff가 복구되지 않는다.

## 2026-05-06 java-only asymmetric seeds candidate

- `probe_java_rust_mixed_membership.sh`에 optional asymmetric seed path(`JAVA_RUST_MIXED_MEMBERSHIP_USE_ASYMMETRIC_SEEDS=1`)를 추가했다.
- `JAVA_RUST_MIXED_MEMBERSHIP_INITIAL_CLUSTER_MANAGER_NODES=java-primary-1` 위에서 actual probe한 fresh run `/tmp/java-rust-mixed-membership.java-only-asym`는 formed-only handoff를 만들지 못했고 final report도 `membership_formed=false`, `failure_stage=membership_timeout`, `observed_node_count=1`이었다.
- checker `check_java_only_asymmetric_seeds_does_not_restore.py` 결과도 baseline java-only와 asymmetric candidate가 둘 다 `tcp_total=1`, `follow_up_count=0`, `remote_eof_count=1`로 같았다.
- 따라서 same 1-node observed state에서는 asymmetric seed split도 follow-up/formed handoff를 복구하지 못한다.

## 2026-05-06 skip seed peer identity manifest candidate

- `probe_java_rust_mixed_membership.sh`에 optional `JAVA_RUST_MIXED_MEMBERSHIP_SKIP_SEED_PEER_IDENTITY_MANIFEST=1` path를 추가했다.
- `JAVA_RUST_MIXED_MEMBERSHIP_INITIAL_CLUSTER_MANAGER_NODES=java-primary-1` 위에서 actual probe한 fresh live report `/tmp/java-rust-mixed-membership.java-only-no-manifest.live.json`는 `membership_formed=false`, `observed_node_count=1`이었지만
  - `steelsearch_bootstrap_remote_nodes=[]`
  - `steelsearch_membership_members=[]`
  - `steelsearch_transport_accepting_connections=false`
  - `steelsearch_transport_handshake_accepted=false`
  - `steelsearch_native_transport_join_participation=false`
  로 악화됐다.
- checker `check_skip_seed_peer_identity_manifest_worsens_readiness.py` 결과도 baseline java-only 대비 readiness 악화를 보였고, result는 `skipping_seed_peer_identity_manifest_worsens_transport_readiness_and_is_not_a_restore_candidate`였다.

## 2026-05-06 aggressive ping schedule candidate

- stronger formed producer restore candidate로 `JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_PING_SCHEDULE=200ms`를 `JAVA_RUST_MIXED_MEMBERSHIP_INITIAL_CLUSTER_MANAGER_NODES=java-primary-1` 위에서 actual probe했다.
- fresh run `/tmp/java-rust-mixed-membership.java-only-ping`은 formed-only handoff를 만들지 못했고 final report도 `membership_formed=false`, `failure_stage=membership_timeout`, `observed_node_count=1`이었다.
- checker `check_java_only_ping_schedule_does_not_restore.py` 결과도 baseline java-only와 ping candidate가 둘 다 `tcp_total=1`, `follow_up_count=0`, `remote_eof_count=1`로 같았다.
- 따라서 aggressive ping schedule도 same 1-node observed state에서 follow-up/formed handoff를 복구하지 못한다.

## 2026-05-06 same 1-node restore family practical stop

- checker `check_same_one_node_candidate_matrix_practical_stop.py`를 추가했다.
- same 1-node observed state 후보군
  - `java-only-icmn`
  - `java-only-icmn-15s`
  - `java-only-asym`
  - `java-only-no-manifest`
  - `java-only-ping`
  을 actual matrix로 묶어 보면 전부 `membership_formed=false`, `observed_node_count<=1`, `follow_up_count=0`이다.
- checker result는 `same_one_node_restore_candidate_matrix_reached_practical_stop_without_restoring_followup_or_formed_handoff`였다.
- 따라서 current same-1-node restore family는 practical stop에 도달했고, 다음 생산적 step은 이 family 바깥의 broader formed producer restore family 또는 backlog branch로 pivot하는 것이다.

## 2026-05-06 next family after same 1-node stop

- checker `check_next_family_after_same_one_node_stop.py`를 추가했다.
- actual CRUD `prepare` gate artifact(`/tmp/rust-primary-java-replica-readygate-direct/prepare-phase.json`)는 여전히
  - `prepare_ready_gate=false`
  - `prepare_ready_node_count=0`
  - `prepare_ready_error=TimeoutError: timed out`
  이다.
- same 1-node stop matrix(`/tmp/same-one-node-stop.json`)는 `same_one_node_restore_candidate_matrix_reached_practical_stop_without_restoring_followup_or_formed_handoff`였다.
- checker result는 `next_productive_branch_is_broader_formed_producer_restore_family_not_actual_run_backlog`였다.
- 따라서 다음 생산적 branch는 actual run backlog가 아니라 broader formed producer restore family다.

## 2026-05-06 no split build run candidate

- broader formed producer restore candidate로 `STEELSEARCH_SPLIT_BUILD_RUN`을 제거한 no-split launch mode를 actual probe했다.
- fresh run `/tmp/java-rust-mixed-membership.no-split`은 formed-only handoff를 만들지 못했고 live report도 `membership_formed=false`, `observed_node_count=0`, `failure_stage=live_handoff_ready`였다.
- checker `check_no_split_build_run_does_not_restore.py` 결과도 zero-node baseline(`/tmp/java-rust-mixed-membership.formed-only-fresh.live.json`)과 no-split candidate가 둘 다 `tcp_total=17`, `follow_up_count=0`, `remote_eof_count=17`로 같았다.
- 따라서 no-split launch mode도 broader formed producer restore candidate로는 실패다.

## 2026-05-06 production mode candidate

- broader formed producer restore candidate로 `JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_MODE=production`를 actual probe했다.
- fresh live report `/tmp/java-rust-mixed-membership.production-mode.live.json`는 `membership_formed=false`, `observed_node_count=0`, `blocker_class=production_mode_blocked`였고 formed-only handoff도 생성되지 않았다.
- checker `check_production_mode_worsens_restore_readiness.py` 결과도 zero-node baseline 대비 `transport_accepting_connections=true -> false`, `transport_handshake_accepted=true -> false`, `production_mode_blocked=false -> true`였다.
- 따라서 production mode forcing은 restore candidate가 아니라 fail-closed candidate다.

## 2026-05-06 broader launch-env restore family practical stop

- checker `check_broader_restore_family_practical_stop.py`를 추가했다.
- broader launch/env restore family
  - `no-split`
  - `production-mode`
  를 actual matrix로 보면 둘 다 `membership_formed=false`, `follow_up_count=0`이며 checker result는 `broader_launch_env_restore_family_reached_practical_stop_without_restoring_followup_or_formed_handoff`였다.
- 이어서 checker `check_next_branch_after_broader_restore_stop.py`로 actual CRUD `prepare` gate artifact와 함께 판정한 결과는 `next_productive_branch_is_source_level_restore_candidate_not_more_launch_env_knobs_or_actual_run_backlog`였다.
- 따라서 다음 생산적 branch는 launch/env knob 추가 탐색이 아니라 source-level formed producer restore candidate다.
- 2026-05-07: late-window `perf record -g` + `jcmd Thread.print` 매핑 결과 main payload tids `350281/350390/350275/350279/350280`는 `opensearch[java-primary-1][generic][T#1..5]`로 잡혔고 `UnixFileDispatcherImpl.read0`를 수행했다. 왜 starvation same-socket payload read의 main path가 Netty `transport_worker` event loop가 아니라 OpenSearch `generic` pool thread에서 관측되는지 source-level dispatch path 설명이 아직 필요하다.
- 2026-05-07: payload read main path는 `opensearch[java-primary-1][generic][T#1..5]` + `UnixFileDispatcherImpl.read0`까지는 actual로 고정됐지만, visible `TcpTransport`/`TransportService`/`TransportHandshaker` source는 `generic`을 post-read dispatch/timeout executor로만 드러낸다. `read0` 위 higher Java caller frame을 더 확보해 same-socket payload read의 concrete generic-pool Java path를 설명해야 한다.
- 2026-05-07: repeated `jcmd Thread.print` 36회 샘플링은 main generic payload tids를 모두 `LinkedTransferQueue.take` parking 상태로만 잡았고 `Attach Listener` read noise도 크게 만들었다. 따라서 `UnixFileDispatcherImpl.read0` 위 higher Java caller는 repeated `jcmd`로는 복구되지 않았고, non-intrusive `perf script`/JIT symbol path가 필요하다.
- 2026-05-07: non-intrusive `perf script` + `/tmp/perf-<pid>.map` symbolization candidate를 actual로 돌렸지만 late failing window에서 `perf_map_copied=false`였다. current JVM/process가 perf-map JIT symbol export를 기본으로 내주지 않는 이유와, 이를 켤 수 있는 launch/env candidate가 무엇인지 확인이 필요하다.
- 2026-05-07: `OPENSEARCH_JAVA_OPTS='-XX:+UnlockDiagnosticVMOptions -XX:+DebugNonSafepoints -XX:+PreserveFramePointer -XX:+DumpPerfMapAtExit'`는 child OpenSearch launch env에 실제로 전달됐지만 `/tmp/perf-<pid>.map` export는 복구하지 못했다. `DumpPerfMapAtExit`가 이 launch mode/probe 종료 방식에서 왜 map을 만들지 않는지, 그리고 대체 가능한 non-intrusive JIT symbol path가 무엇인지 확인이 필요하다.
- 2026-05-07: perf-side candidate `sudo perf inject -j`도 failing perf.data에서 `jit_lines=0`, `unknown_tmp_perf_lines=18881`로 끝났다. current non-intrusive JIT symbol family가 practical stop인지, 아니면 아직 시도할 perf/JVM candidate가 남아 있는지 판단이 필요하다.
- 2026-05-07: `DumpPerfMapAtExit`, `perf inject --jit`, repeated `jcmd`까지 모두 higher caller 복구에 실패했다. non-intrusive JIT symbol family practical stop을 current Java inbound response delivery/read-starvation root blocker와 어떻게 문서상 연결할지가 남아 있다.
- 2026-05-07: non-intrusive JIT symbol family practical stop은 별도 새 branch가 아니라 기존 Java inbound response delivery/read-starvation root blocker로 재합류한다는 actual evidence가 나왔다. 이제 이 결론을 broader mixed actual-run backlog blocked state와 어떻게 연결해 기록할지가 남아 있다.
- 2026-05-07: current mixed actual-run subtree는 `prepare_ready_gate=false` 자체가 독립 문제라기보다 Java inbound response delivery/read-starvation root blocker의 하위 blocked state라는 actual evidence가 고정됐다. 이 practical stop을 보존한 채 다음 productive backlog branch를 어디로 잡을지가 남아 있다.
- 2026-05-07: actual-run family 내부 sibling (`bulk replay`, `rolling restart`)로 옮기는 것은 productive하지 않다는 actual evidence가 생겼다. 다음 단계는 root-blocker relief candidate를 다시 여는지, 아니면 independent non-actual-run backlog branch로 옮길지 결정하는 것이다.
- 2026-05-07: 남은 top-level unchecked branch가 모두 actual-run family라서, independent non-actual-run backlog로는 pivot할 수 없다는 actual evidence가 나왔다. 다음 직접 작업은 root-blocker relief candidate를 다시 고르는 것이다.
- 2026-05-07: `sudo perf record --call-graph dwarf` candidate도 `read -> UnixFileDispatcherImpl.read0`까지만 남고 higher caller를 복구하지 못했다. 이제 current root-blocker relief candidate family 전체가 practical stop인지 판단해야 한다.
- 2026-05-07: root-blocker relief candidate family(`DumpPerfMapAtExit`, `perf inject --jit`, `perf --call-graph dwarf`)도 higher caller 복구 없이 practical stop으로 닫혔다. 이 stop을 broader read-starvation blocker/session stop point와 어떻게 연결해 기록할지가 남아 있다.
- 2026-05-07: relief family practical stop, actual-run blocked state, next-branch 판정이 모두 같은 read-starvation session stop point로 수렴한다는 actual evidence가 고정됐다. 이제 남은 질문은 materially different external capability 또는 새 relief candidate가 생기기 전까지 이 subtree를 blocked로 유지할지 여부다.
- 2026-05-07: current session 기준 read-starvation subtree는 materially different external capability 또는 새 root-blocker relief candidate가 생기기 전까지 blocked로 유지해야 한다는 actual evidence가 고정됐다. 즉시 재개 조건을 무엇으로 볼지 나중에 명확히 해야 한다.
- 2026-05-07: `strace` binary 존재는 false positive였다. current session에서는 ptrace attach가 `Operation not permitted`로 막혀 있어 actually usable한 materially different capability로 볼 수 없다.
- 2026-05-07: current session에서는 `strace`도 usable하지 않아 blocked subtree를 유지해야 한다는 actual evidence가 고정됐다. 즉시 재개 조건은 "binary presence"가 아니라 실제 attach/trace 가능한 capability 확보여야 한다.
- 2026-05-07: usable materially different capability는 `sudo strace`였다. subtree 재개 자체는 성공했으므로, 다음 핵심 질문은 late failing window에서 어떤 fd/thread ordering으로 `epoll_pwait/read/close`가 섞이는지다.
- 2026-05-07: late `sudo strace` parser 결과 selector-like tids `360850/360861/360865`는 `epoll_pwait(181/183/185)`와 `read(fd=182/184/186)` eventfd path가 주류였고, main read-only tids `360854/360858/360859/360860`가 `fd=191/193/194` majority read/close를 담당했다. 다만 selector thread에도 occasional `fd=191` read/close가 있고, 이번 sample의 `fd=191/193` payload 일부는 `"max 100000\\n"` 같은 `/proc`-like text로 보여 numeric fd reuse/noise 가능성이 아직 남아 있다. 따라서 same-socket starvation payload path가 selector handoff인지, 아니면 fd reuse/noise인지 late strace artifact만으로 더 분리할 필요가 있다.
- 2026-05-07: fresh `sudo strace -yy -s 256` run(`/tmp/java-rust-mixed-membership.sudo-strace-late-yy`)에서는 selector tids에 `fd=191/193/194` activity가 아예 안 나왔고, global `fd=191/193/194`는 mostly `/proc`/cgroup `proc` role + 일부 `TCPv6` role이 섞였다. 즉 이전 plain strace에서 본 selector occasional `fd=191`은 numeric fd reuse/noise 쪽이 더 강해졌다. 다만 non-selector tids `362276/362285/362288` 등에서 `fd=191:TCPv6[[::ffff:127.0.0.1]:...]`가 실제로 보여, 이 TCPv6 path가 starvation socket tuple family와 같은 actual same-socket payload read인지 아니면 별도 helper/noise path인지는 아직 남아 있다.
- 2026-05-07: checker `check_late_strace_tcpv6_vs_capture.py`로 위 ambiguity를 줄인 결과, non-selector tids `362276/362285/362288`의 `fd=191` TCPv6 local ports `{35040,56404,59510,59514,59526,59530,59546}`는 same run `transport-seed-capture.json`의 `peer_addr` port set과 실제 overlap했고 remote port도 항상 `STEELSEARCH_TRANSPORT_PORT=43871`이었다. 즉 actual same-socket payload read path는 selector가 아니라 non-selector thread path라는 점은 고정됐다. 남은 질문은 이 non-selector tids가 Java `generic` pool인지, 아니면 다른 helper pool/thread role인지다.
- 2026-05-07: fresh same-run `sudo strace + jcmd` artifact(`/tmp/java-rust-mixed-membership.sudo-strace-jcmd-late`)에서는 same-socket tuple tids `363714/363722/363726`가 실제로 `opensearch[java-primary-1][transport_worker][T#1..3]`로 매핑됐다. 즉 “same-socket payload read는 generic pool” 가설은 late strace same-run 기준으로는 깨졌다. 대신 새 ambiguity는, 이 tids가 transport_worker인데도 current strace parser의 epoll selector set에는 포함되지 않았다는 점이다. 다음 확인 포인트는 same tids의 syscall mix가 `epoll_pwait`가 아니라 `ppoll/read/close` 쪽으로 바뀐 것인지, 아니면 current epoll detector가 놓친 것인지다.
- 2026-05-07: same-run syscall mix checker 결과 `363714/363722/363726`는 실제로 `epoll_pwait` 31~36회와 `read_eventfd` 16~22회를 수행했고, 그 same tids 안에서 `ppoll(fd=191<TCPv6...>) -> read(fd=191) -> close(fd=191)`도 같이 열렸다. 즉 “transport_worker인데 epoll set에 안 보인다”는 ambiguity는 `-yy` format에서 `epoll_pwait(183<anon_inode:[eventpoll]>, ...)`를 놓친 detector bug였다. 남은 질문은 왜 same transport_worker thread가 `epoll_pwait/eventfd` loop와 별도로 `ppoll(fd=191)` branch까지 같이 수행하는지다.
- 2026-05-07: ordering checker 결과 same `transport_worker T#1..3` 안에서 `EPOLLOUT(fd191)` -> `ppoll(POLLOUT fd191)` -> `EPOLLIN(fd191)` -> `read(fd191)=29B` -> `close(fd191)`가 실제로 반복됐다. 즉 `ppoll(fd191)` branch는 별도 helper thread path가 아니라 same transport_worker 안의 inline socket-readiness + direct payload read path다. 이제 남은 direct question은 이 direct payload read가 왜 higher Java/Netty marker(`channelRead`, `response_read`)로는 여전히 보이지 않느냐이다.
- 2026-05-07: same-run checker 결과 `transport_worker`의 direct TCP payload read는 actual로 `7`회 있었지만, 같은 run `stdout.log` marker는 `response_read=0`, `handle_response=0`, `execute_handshake_listener_onResponse=0`, `channelRead=0`, `netty_channel_read=0`, `open_response=0`, `execute_handshake_listener_onFailure=62`였다. 즉 current boundary는 `Socket/JDK read` 위, `Netty response dispatch` 아래로 더 좁혀졌다. 이제 남은 질문은 이 29-byte payload 자체가 정말 low-level handshake response frame인지, 아니면 다른 small control frame인지다.
- 2026-05-07: `check_transport_worker_29b_payload_identity.py` 결과 same-run `transport_worker`가 읽은 `29B` payload 7개는 모두 Steelsearch capture의 `response_frame`과 exact match했다. 즉 이 payload는 다른 small control frame이 아니라 actual low-level `internal:tcp/handshake` response frame이다. 그런데 같은 run에서 `handle_response=0`, `response_read=0`, `execute_handshake_listener_onResponse=0`였으므로, 남은 direct gap은 “exact low-level handshake response frame read -> TransportHandshaker.handleResponse” 사이의 dispatch 경로다.
- 2026-05-07: `check_dispatch_gap_before_handle_response.py` 결과 same-run exact response read ports `{39838,39850,39858,39866,39878,55112,55120}`와 `steelsearch_inbound_pipeline_stage=handle_bytes` marker port `{53534}`는 겹치지 않았다. 즉 current boundary는 `TransportHandshaker.handleResponse` 이전일 뿐 아니라, same-socket 기준으로는 `InboundPipeline.handleBytes` 이전으로 더 좁혀졌다. 남은 질문은 `SocketChannelContext.handleReadBytes -> channelHandler.consumeReads` 내부 어디에서 same-socket exact response frame이 빠지는지다.
- 2026-05-07: source+artifact checker 결과 current best boundary는 `production NioChannelHandler.consumeReads` 이전/내부다. source상 `BytesChannelContext.read -> readFromChannel -> handleReadBytes -> channelHandler.consumeReads`는 고정됐고, mock concrete handler는 `consumeReads -> pipeline.handleBytes`를 바로 호출한다. 그런데 same-run exact response ports는 actual `handleBytes` marker까지 도달하지 않았다. 따라서 다음 직접 질문은 production concrete `consumeReads` 구현체가 정확히 어디인지, 그리고 same-socket exact response frame이 그 구현체 안에서 실제로 빠지는지다.
- 2026-05-07: production transport callsite를 더 직접 확인한 결과, 실제 `pipeline.handleBytes(...)`는 `modules/transport-netty4/.../Netty4MessageChannelHandler.channelRead(...)`에서 호출된다. same-run artifact에서는 `steelsearch_netty4_message_channel_stage=channel_read`가 port `53534`에서만 찍혔고, exact low-level handshake response ports `{39838,39850,39858,39866,39878,55112,55120}`와는 겹치지 않았다. 따라서 current best boundary는 mock `consumeReads` 예시보다 더 직접적으로, `Netty4MessageChannelHandler.channelRead` 이전 handoff gap이다.
- 2026-05-07: production source까지 합치면 transport workers는 `MultiThreadIoEventLoopGroup(..., NioIoHandler.newFactory())`에서 나오고, `pipeline.handleBytes(...)`는 `Netty4MessageChannelHandler.channelRead(...)` 안에서만 호출된다. same-run exact response frames는 `transport_worker`에서 actual read됐지만 `channelRead` marker와는 겹치지 않았다. 따라서 current best boundary는 `Netty NioIoHandler/ByteBuf handoff -> Netty4MessageChannelHandler.channelRead` 사이이며, 다음 직접 질문은 repo 밖 Netty 내부 handoff를 어떤 artifact로 더 들여다볼 수 있느냐다.
- 2026-05-07: local Netty jar `netty-transport-4.2.12.Final.jar`의 `AbstractNioByteChannel$NioByteUnsafe.read()` bytecode를 actual로 열어보니 read path는 `doReadBytes(ByteBuf)` 뒤 즉시 `ChannelPipeline.fireChannelRead(ByteBuf)`였다. same-run exact response frame은 `transport_worker`에서 actual read됐지만 OpenSearch `Netty4MessageChannelHandler.channelRead` marker까지는 오지 않았다. 따라서 current best boundary는 `Netty internal doReadBytes -> fireChannelRead -> handler invocation` 구간이며, 다음 질문은 `DefaultChannelPipeline.fireChannelRead` 이후 handler invocation bytecode까지 더 파서 narrowing을 이어갈지, 아니면 current session practical stop으로 볼지다.
- 2026-05-07: `AbstractChannelHandlerContext.fireChannelRead(Object)` bytecode까지 실제로 확인한 결과, Netty inbound dispatch는 `findContextInbound(32)` -> `executor.inEventLoop()` -> 같은 event-loop면 즉시 `ChannelInboundHandler.channelRead(...)`, 아니면 `EventExecutor.execute(...)` 비동기 fallback이라는 두 갈래뿐이었다. same-run artifact에서는 exact low-level handshake response frame 7개가 `transport_worker`에서 actual read됐지만 `Netty4MessageChannelHandler.channelRead` port set과는 여전히 overlap이 0이고 `response_read/handle_response`도 0이었다. 따라서 current session 기준 current best boundary는 더 이상 repo 안으로 줄지 않으며, `repo 밖 Netty internal handoff(doReadBytes -> fireChannelRead -> handler invocation)`가 practical stop point다.
- 2026-05-07: checker `check_netty_internal_stop_matches_read_starvation_block.py` 결과 위 Netty internal handoff practical stop은 별도 새 branch가 아니라 기존 `read_starvation_subtree_should_remain_blocked_until_materially_different_capability_or_new_relief_candidate_appears` blocked state로 재합류했다. 즉 다음 전진 조건은 repo 안 source patch가 아니라 materially different Netty/JVM/native visibility capability 또는 진짜 새 relief candidate다.
- 2026-05-07: checker `check_netty_stop_preserves_blocked_state.py`까지 합치면, 현재 read-starvation subtree는 `repo 밖 Netty internal handoff` practical stop을 포함한 채 `materially different Netty/JVM/native capability 또는 새 relief candidate`가 실제로 생길 때까지 blocked 상태로 유지해야 한다는 actual evidence가 고정됐다. 다시 말해 현 단계의 부족분은 source patch가 아니라 visibility/capability 차이다.
- 2026-05-07: `CFR 0.152` decompiler를 local capability로 실제 확보해 Netty `AbstractNioByteChannel` / `AbstractChannelHandlerContext` decompile source를 열었다. 결과는 `doReadBytes(byteBuf) -> pipeline.fireChannelRead(byteBuf) -> findContextInbound(32) -> same-thread ChannelInboundHandler.channelRead(...) or async executor fallback`를 source 형태로 재확인한 것이고, same-run marker는 여전히 `response_read=0`, `handle_response=0`이었다. 즉 `CFR`는 materially different visibility capability이긴 했지만 current repo-external Netty internal handoff boundary를 넘어서는 relief는 아니었다.
- 2026-05-07: `sudo jhsdb jstack --pid`는 current host에서 실제 usable한 materially different JVM/native capability였다. same failing window collector `run_probe_with_late_strace_and_jhsdb.py`로 확보한 artifact(`/tmp/java-rust-mixed-membership.sudo-strace-jhsdb-late`)에서 late strace same-socket `TCPv6` tids `369451/369462/369466`는 checker `check_late_strace_jhsdb_transport_worker_roles.py` 기준 `opensearch[java-primary-1][transport_worker][T#1..3]`로 다시 매핑됐다. 즉 subtree는 이 capability로 실제 재개됐고, 다음 질문은 이 mixed-stack artifact에서 transport_worker의 concrete Java/native frames를 더 직접 뽑아 gap을 줄일 수 있느냐다.
- 2026-05-07: checker `check_late_jhsdb_transport_worker_frames.py` 결과 same-run `TCPv6` tids `369451/369462/369466`의 mixed stack은 `sun.nio.ch.EPoll.wait -> EPollSelectorImpl.doSelect -> io.netty.channel.nio.NioIoHandler.select/run -> SingleThreadIoEventLoop.runIo`였다. 즉 `transport_worker` selector path 자체는 mixed stack으로 고정됐지만, 이번 snapshot은 exact 29-byte handshake response read 순간이 아니라 `EPoll.wait` 시점을 잡았다. 다음 질문은 repeated/tighter `jhsdb` sampling으로 exact payload-read 순간 frame을 실제로 잡을 수 있느냐다.
- 2026-05-07: repeated collector `run_probe_with_repeated_jhsdb_and_late_strace.py`로 late 15초 window 동안 `jhsdb` snapshot 42개를 실제로 수집했지만, checker `check_repeated_jhsdb_exact_read_frames.py` 결과 same-socket tids `370835/370843/370847`에 대해 `UnixFileDispatcherImpl.read0`, `SocketDispatcher.read0`, `NioSocketChannel.doReadBytes`, `AbstractNioByteChannel$NioByteUnsafe.read` hit는 하나도 없었다. 즉 repeated `jhsdb` sampling도 exact payload-read 순간 frame을 못 잡았고, 다음 질문은 더 tighter/triggered mixed-stack capture 또는 다른 materially different capability가 필요한지다.
- 2026-05-07: built-in `JFR` capability도 actual로 검증했다. collector `run_probe_with_late_jfr.py`로 same failing window `/tmp/java-rust-mixed-membership.late-jfr`를 수집했고 checker `check_late_jfr_transport_worker_samples.py` 결과 `transport_worker_samples=746`, `EPoll.wait=746`, `EPollSelectorImpl.doSelect=746`, `NioIoHandler.select=746`였지만 `UnixFileDispatcherImpl.read0=0`, `SocketDispatcher.read0=0`, `NioSocketChannel.doReadBytes=0`였다. 즉 JFR는 `jhsdb`와 달리 high-volume selector-path confirmation은 주지만 exact payload-read frame은 여전히 못 잡는다.
- 2026-05-07: `async-profiler`도 materially different capability로 actual 확보했다. 처음에는 `linux-x64` build를 잘못 받아 `aarch64` host에서 실행이 안 됐고, 이후 `linux-arm64` build로 교체하자 `wall` event attach가 정상 동작했다. collector `run_probe_with_late_async_profiler_wall.py`로 same failing window `/tmp/java-rust-mixed-membership.async-wall`를 수집했고 checker `check_late_async_profiler_wall_samples.py` 결과 `transport_worker=5`, `EPoll.wait=3`, `NioIoHandler.select=3`이 잡혔지만 `UnixFileDispatcherImpl.read0=0`, `SocketDispatcher.read0=0`, `NioSocketChannel.doReadBytes=0`, `AbstractNioByteChannel$NioByteUnsafe.read=0`였다. 즉 `async-profiler wall`도 selector path confirmation까지만 제공했고 exact payload-read frame은 못 잡았다.
- 2026-05-07: stronger targeted candidate로 `async-profiler -e io.netty.channel.socket.nio.NioSocketChannel.doReadBytes`를 same failing window `/tmp/java-rust-mixed-membership.async-method`에 실제로 붙였다. checker `check_late_async_profiler_method_samples.py` 결과 `transport_worker=3`, `NioSocketChannel.doReadBytes=3`, `AbstractNioByteChannel$NioByteUnsafe.read=3`이 잡혔고, 이는 selector path보다 한 단계 아래의 exact Netty read-side method까지 actual로 내려간 첫 artifact다. 다만 `SocketDispatcher.read0`와 `UnixFileDispatcherImpl.read0`는 여전히 0이어서, 다음 질문은 native-wrapper read boundary를 직접 겨냥한 event/method candidate가 가능한지다.
- 2026-05-07: direct native-wrapper candidate로 `async-profiler -e sun.nio.ch.SocketDispatcher.read0`와 `-e sun.nio.ch.UnixFileDispatcherImpl.read0`를 각각 same failing window에 붙였지만 두 run 모두 sample hit가 0이었다. checker `check_native_wrapper_read_candidates.py` 결과는 `direct_native_wrapper_async_profiler_method_candidates_did_not_capture_exact_native_read_boundary`였다. 즉 exact native read boundary를 잡기 위해서는 direct native-wrapper method name보다 한 단계 위 wrapper(`IOUtil.read` 등)나 다른 event plane이 필요할 가능성이 높다.
- 2026-05-07: higher wrapper candidate `async-profiler -e sun.nio.ch.IOUtil.read`는 same failing window `/tmp/java-rust-mixed-membership.async-ioutil-read`에서 actual hit가 났다. checker `check_higher_wrapper_read_candidate.py` 결과 `IOUtil.read=131`, `transport_worker=9`, `NioSocketChannel.doReadBytes=9`, `AbstractNioByteChannel$NioByteUnsafe.read=9`였고, 이는 boundary를 direct native-wrapper 0-hit보다 한 단계 더 아래의 JDK wrapper read path까지 내린 것이다. 다만 `SocketDispatcher.read0`/`UnixFileDispatcherImpl.read0`는 여전히 0이어서, 다음 질문은 `readIntoNativeBuffer`나 `SocketDispatcher.read` 같은 중간 wrapper가 native read0 바로 위 boundary를 더 직접 드러내는지다.
- 2026-05-07: 중간 wrapper candidate `sun.nio.ch.IOUtil.readIntoNativeBuffer`와 `sun.nio.ch.SocketDispatcher.read`도 actual hit가 났다. checker `check_mid_wrapper_read_candidates.py` 결과 `IOUtil.readIntoNativeBuffer=37`, `SocketDispatcher.read=3`, 그리고 두 경우 모두 `IOUtil.read`, `NioSocketChannel.doReadBytes`, `AbstractNioByteChannel$NioByteUnsafe.read`가 함께 보였다. 즉 current boundary는 이제 `SocketDispatcher.read` / `IOUtil.readIntoNativeBuffer`까지 내려왔다. 하지만 `SocketDispatcher.read0`와 `UnixFileDispatcherImpl.read0`는 여전히 0이어서, 남은 질문은 `SocketDispatcher.read -> read0`의 마지막 native call transition을 어떤 capability/event plane으로 잡을 수 있느냐다.
## 2026-05-07 async-profiler native transition gap

- same failing window에서 `async-profiler` method event + `--cstack dwarf`는
  - `sun.nio.ch.SocketDispatcher.read`
  - `sun.nio.ch.IOUtil.readIntoNativeBuffer`
  까지는 actual로 잡았지만,
  - `SocketDispatcher.read0`
  - `UnixFileDispatcherImpl.read0`
  - `Java_sun_nio_ch_*_read0`
  는 전부 0이었다.
- collapsed stack tail도 `Instrument::recordSample -> Profiler::getNativeTrace`까지만 보여서, 현 plane의 direct boundary는 `SocketDispatcher.read`로 보인다.
- 남은 질문:
  - exact `read0` callee boundary를 잡으려면 다음 capability를
    - `perf probe/uprobe`
    - `bpftrace`
    - 다른 JNI/native-transition aware plane
    중 어디로 두는 게 가장 현실적인가?

## 2026-05-07 perf uprobe read0 hit 이후 남은 correlation

- `perf probe/uprobe`는 actual로 성공했다.
  - `probe_libnio:ss_socket_read0=7`
  - `probe_libnio:ss_unix_read0=126`
- 따라서 exact native callee boundary 자체는 더 이상 unknown이 아니다.
- 남은 질문:
  - `ss_socket_read0=7`이 same-run starvation same-socket handshake response branch와 정확히 같은 branch인지
  - `ss_unix_read0=126`은 transport_worker same-socket path가 아니라 background file/cgroup/process-monitor noise인지
  를 same-run tuple/marker artifact와 어떻게 가장 깔끔하게 묶을 것인가?

## 2026-05-07 same-run strace+uprobe after correlation

- same-run combined collector(`/tmp/java-rust-mixed-membership.strace-uprobe-late`)로는
  - `probe_libnio:ss_socket_read0=10`
  - `probe_libnio:ss_unix_read0=124`
  - selector tuple tids only
  - `response_read=0`, `handle_response=0`, `netty_channel_read=0`
  까지는 actual로 묶였다.
- checker `check_same_run_uprobe_vs_tuple_branch.py` 기준:
  - `ss_socket_read0`는 starvation same-socket selector branch와 정렬
  - `ss_unix_read0`는 broader background IO
  로 보는 편이 맞다.
- 다만 같은 run에서 `check_transport_worker_29b_payload_identity.py`는 exact 29-byte payload match를 재현하지 못했다.
- 남은 질문:
  - combined run에서 exact 29-byte handshake payload identity가 비는 이유가
    - sampling/timing window 차이인지
    - strace attach perturbation인지
    - fd/path scheduling 차이인지
  를 어떻게 가장 직접적으로 분리할 것인가?

## 2026-05-07 combined strace+uprobe mismatch explanation

- checker `check_combined_strace_uprobe_timing_artifact.py` 기준:
  - `strace-only`: exact handshake reads `7`, transport-worker 29B reads `7`
  - `uprobe-only`: `ss_socket_read0=7`
  - `combined strace+uprobe`: `ss_socket_read0=10`, exact handshake reads `0`
- 현재 best explanation:
  - combined collector는 `socket_read0` branch 자체는 유지하지만
  - ptrace `strace` attach가 fine-grained exact `29-byte` payload identity 재현을 흔드는 timing perturbation을 만든다.
- 남은 질문:
  - same-run correlation을 유지하면서도 ptrace `strace`보다 덜 intrusive한 plane으로
    - socket tuple identity
    - exact 29-byte payload identity
    - `ss_socket_read0`
  를 함께 보려면 무엇을 써야 하는가?

## 2026-05-07 low-intrusion same-run proof

- windowed low-intrusion run(`/tmp/java-rust-mixed-membership.perf-uprobe-read0-windowed`)에서
  - `probe_libnio:ss_socket_read0=7`
  - late perf window 안 exact handshake response frames `=7`
  - request ids `10..16`
  - frame sizes `23 bytes`
  - Java markers `response_read=0`, `handle_response=0`, `netty_channel_read=0`
  를 same-run으로 actual 확인했다.
- 즉 ptrace `strace` 없이도
  - exact response frame identity
  - native `SocketDispatcher.read0` hit
  - Java dispatch marker zero
  를 한 run 안에서 함께 보이는 plane은 확보됐다.
- 남은 질문:
  - 이 stronger low-intrusion evidence를 현재 `repo-external Netty internal handoff` practical stop과 어떻게 가장 깔끔하게 재연결할 것인가?

## 2026-05-07 low-intrusion proof rejoin

- checker `check_low_intrusion_proof_rejoins_netty_stop.py` 결과:
  - `low_intrusion_same_run_read0_proof_rejoins_existing_repo_external_netty_handoff_practical_stop_and_preserves_read_starvation_root_blocker`
- 의미:
  - stronger low-intrusion proof도 새 해결축을 열지 않는다.
  - exact `23-byte` handshake response frame이 `SocketDispatcher.read0`까지 actual로 도달했는데도 `response_read/channelRead`가 0이라는 사실이, 기존 `repo-external Netty internal handoff` practical stop을 더 강하게 지지한다.
- 남은 질문:
  - 이제 필요한 것은
    - materially different repo-external Netty/native visibility capability
    - 또는 genuinely new relief candidate
  둘 중 어느 쪽인가?

## 2026-05-07 stronger proof blocked-state preservation

- capability frontier scan 결과:
  - `bpftrace=null`
  - `tcpdump=null`
  - `tshark=null`
  - `ngrep=null`
  - `available_new_repo_external_planes=[]`
- final checker 결과:
  - `stronger_low_intrusion_proof_still_requires_preserving_blocked_practical_stop_until_new_repo_external_capability_or_relief_candidate_appears`
- 의미:
  - stronger low-intrusion proof가 생겨도 현재 host에서 추가로 쓸 수 있는 새 repo-external visibility plane binary는 확인되지 않았다.
  - 따라서 subtree는 blocked practical stop으로 다시 보존하는 편이 맞다.

## 2026-05-07 broader actual-run family block reconfirmed

- checker `check_stronger_stop_blocks_actual_run_family.py` 결과:
  - `stronger_read_starvation_practical_stop_still_blocks_the_entire_broader_actual_run_family`
- 의미:
  - stronger practical stop은 좁은 read-side subtree만 막는 것이 아니라,
  - 남아 있는 broader mixed actual-run family 전체를 계속 막는다.

## 2026-05-07 actual-run family blocked-state preservation

- checker `check_actual_run_family_blocked_until_new_capability.py` 결과:
  - `broader_actual_run_family_should_remain_blocked_until_materially_different_capability_or_genuinely_new_relief_candidate_appears`
- 의미:
  - 현재 broader actual-run family 전체는 blocked practical stop으로 유지하는 편이 맞다.
  - 다음 직접 질문은 이 family 밖에 즉시 진행 가능한 non-blocked leaf가 실제로 남아 있느냐이다.

## 2026-05-07 top-level backlog recheck

- checker `check_no_nonblocked_leaf_outside_actual_run_family.py` 결과:
  - `no_immediately_actionable_non_blocked_leaf_remains_outside_the_blocked_actual_run_family`
- 의미:
  - top-level backlog 기준으로도 immediate non-blocked leaf는 남아 있지 않다.
  - 현재 남은 것은 blocked actual-run family뿐이다.

## 2026-05-08 top-level backlog preserved as blocked actual-run family

- checker `check_top_level_backlog_only_has_blocked_actual_run_family.py` 결과:
  - `current_top_level_backlog_consists_only_of_the_blocked_actual_run_family_until_new_capability_or_relief_candidate_appears`
- 의미:
  - current top-level backlog는 blocked actual-run family만 남은 상태로 보는 편이 맞다.
  - 다음 직접 전진 조건은 다시:
    - materially different capability
    - genuinely new relief candidate
    둘 중 하나가 실제로 생기는 경우뿐이다.

## 2026-05-08 resume condition still unmet

- expanded capability frontier scan 결과:
  - `bpftrace=null`
  - `tcpdump=null`
  - `tshark=null`
  - `ngrep=null`
  - `trace-cmd=null`
  - `uftrace=null`
  - `stap=null`
  - `sysdig=null`
  - `funclatency=null`
  - `opensnoop-bpfcc=null`
  - `opensnoop=null`
- final checker `check_blocked_actual_run_family_resume_unavailable.py` 결과:
  - `blocked_actual_run_family_cannot_be_resumed_because_no_new_capability_or_relief_candidate_is_currently_available`
- 의미:
  - current session에서는 blocked actual-run family를 실제로 재개할 새 capability나 새 relief candidate가 없다.

## 2026-05-08 resume-unavailable state preserved

- checker `check_resume_unavailable_state_should_be_preserved.py` 결과:
  - `resume_unavailable_state_should_be_preserved_until_new_capability_or_relief_candidate_appears`
- 의미:
  - current session에서는 blocked actual-run family의 resume 불가 상태를 그대로 보존하는 편이 맞다.

## 2026-05-08 current-turn resume trigger check

- checker `check_resume_trigger_still_absent.py` 결과:
  - `resume_trigger_is_still_absent_in_current_turn`
- 의미:
  - 2026-05-08 현재 시점에도 blocked actual-run family를 실제로 재개할 trigger는 아직 없다.

## 2026-05-08 trigger-absence state preserved

- checker `check_resume_trigger_absence_should_be_preserved.py` 결과:
  - `resume_trigger_absence_should_continue_to_be_preserved`
- 의미:
  - current turn 기준으로도 blocked actual-run family 재개 trigger 부재 상태를 그대로 유지하는 편이 맞다.
