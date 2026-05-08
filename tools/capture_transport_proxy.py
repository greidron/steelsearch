#!/usr/bin/env python3
import argparse
import json
import signal
import socket
import threading
import time
from pathlib import Path


def read_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


def action_hint(body: bytes):
    needle = b"internal:"
    start = body.find(needle)
    if start < 0:
        return None
    tail = body[start:]
    end = 0
    while end < len(tail) and 32 <= tail[end] <= 126 and tail[end] != 0:
        end += 1
    try:
        return tail[:end].decode()
    except UnicodeDecodeError:
        return None


def summarize_frame(direction: str, header: bytes, body: bytes):
    summary = {
        "direction": direction,
        "marker_prefix": header[:2].decode(errors="ignore"),
        "message_length": int.from_bytes(header[2:6], "big"),
        "body_len": len(body),
        "body_prefix_hex": body[:96].hex(),
        "ts": time.time(),
    }
    if len(body) >= 13:
        status = body[8]
        summary.update(
            {
                "request_id": int.from_bytes(body[:8], "big", signed=True),
                "status": status,
                "is_request": (status & 0x01) == 0,
                "is_response": (status & 0x01) != 0,
                "is_handshake": (status & 0x08) != 0,
                "version_id": int.from_bytes(body[9:13], "big"),
            }
        )
    hint = action_hint(body)
    if hint:
        summary["action_hint"] = hint
    return summary


def capture_frames(src, dst, direction, capture, lock):
    try:
        while True:
            header = read_exact(src, 6)
            if header is None:
                try:
                    dst.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                return
            length = int.from_bytes(header[2:6], "big")
            body = read_exact(src, length)
            if body is None:
                try:
                    dst.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                return
            with lock:
                capture.append(summarize_frame(direction, header, body))
            dst.sendall(header + body)
    except OSError:
        return


def persist(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-host", required=True)
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--target-host", required=True)
    parser.add_argument("--target-port", type=int, required=True)
    parser.add_argument("--report-path", required=True)
    args = parser.parse_args()

    capture = []
    lock = threading.Lock()
    report_path = Path(args.report_path)
    stop_event = threading.Event()

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((args.listen_host, args.listen_port))
    listener.listen()
    listener.settimeout(1.0)
    persist(report_path, capture)

    def request_stop(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    try:
        while not stop_event.is_set():
            try:
                client, client_addr = listener.accept()
            except socket.timeout:
                continue
            def handle_connection():
                upstream = socket.create_connection((args.target_host, args.target_port))
                with lock:
                    capture.append(
                        {
                            "event": "accepted",
                            "client_addr": f"{client_addr[0]}:{client_addr[1]}",
                            "target_addr": f"{args.target_host}:{args.target_port}",
                            "ts": time.time(),
                        }
                    )
                t1 = threading.Thread(
                    target=capture_frames,
                    args=(client, upstream, "client_to_server", capture, lock),
                    daemon=True,
                )
                t2 = threading.Thread(
                    target=capture_frames,
                    args=(upstream, client, "server_to_client", capture, lock),
                    daemon=True,
                )
                t1.start()
                t2.start()
                t1.join()
                t2.join()
                try:
                    client.close()
                finally:
                    upstream.close()
                persist(report_path, capture)

            threading.Thread(target=handle_connection, daemon=True).start()
    finally:
        persist(report_path, capture)
        listener.close()


if __name__ == "__main__":
    main()
