#!/usr/bin/env python3
import socket
import sys

preferred = int(sys.argv[1]) if len(sys.argv) > 1 else 8560
for port in range(preferred, preferred + 100):
    with socket.socket() as candidate:
        try:
            candidate.bind(("127.0.0.1", port))
            print(port)
            break
        except OSError:
            continue
else:
    raise SystemExit("No free local port found")
