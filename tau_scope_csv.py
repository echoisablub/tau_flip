"""Fetch a full scope trace from the Rohde & Schwarz RTO over Ethernet and save it as CSV.

Usage:
    python tau_scope_csv.py out.csv         # save the acquisition already on the scope
    python tau_scope_csv.py --arm out.csv   # arm a single acquisition, wait, then save

The BLACS plugin blacs/plugins/tau_scope runs the --arm form for every shot.

This script connects directly to the scope via raw TCP socket on port 5025 and saves
columns: time, ch1, ch2, ch3.

It expects the scope to be configured with:
    ch1 = SLM output trigger
    ch2 = PD behind the PBS
    ch3 = reference PD

The file format matches tau_analyse.py:
    python tau_analyse.py trace.csv --hold 14 --out tau_results.csv
"""

import socket
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HOST = "169.254.211.142"
PORT = 5025
CONNECT_TIMEOUT = 5
IO_TIMEOUT = 60
TRIGGER_TIMEOUT = 60
ARM_SETTLE = 0.3


def write(sock, cmd):
    sock.sendall((cmd + "\n").encode())


def read_exact(sock, n):
    buf = bytearray(n)
    view = memoryview(buf)
    got = 0
    while got < n:
        count = sock.recv_into(view[got:])
        if count == 0:
            raise ConnectionError(f"scope closed the connection after {got} of {n} bytes")
        got += count
    return buf


def read_line(sock):
    chunks = []
    while True:
        byte = sock.recv(1)
        if not byte:
            raise ConnectionError("scope closed the connection while reading a response")
        if byte == b"\n":
            return b"".join(chunks).decode("latin-1").strip()
        chunks.append(byte)


def ask(sock, cmd):
    write(sock, cmd)
    return read_line(sock)


def query_binary_block(sock, cmd):
    """Read one complete IEEE 488.2 definite-length block and its line terminator."""
    write(sock, cmd)
    header = read_exact(sock, 2)
    if header[:1] != b"#":
        raise RuntimeError(f"expected a binary block from {cmd!r}, got {bytes(header)!r}")
    num_digits = int(bytes(header[1:2]), 16)
    if num_digits == 0:
        raise RuntimeError(f"indefinite-length block from {cmd!r} is not supported")
    length = int(bytes(read_exact(sock, num_digits)))
    payload = read_exact(sock, length)
    read_line(sock)  # consume the terminator so the next query starts in sync
    return payload


def parse_data_head(head):
    # Example format from RTO: "-0.18902,0.31098,10000000,1"
    parts = [p.strip() for p in head.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Unexpected DATA:HEAD response: {head[:200]!r}")
    x0, x1, n, _ = parts
    return float(x0), float(x1), int(n)


def fetch_and_write(sock, out_path):
    """Read ch1-ch3 of the last acquisition and write them to out_path."""
    write(sock, "FORM:DATA REAL,32")
    write(sock, "FORM:BORD LSBF")
    ask(sock, "*OPC?")

    data = {}
    x0 = x1 = n = None
    for ch in (1, 2, 3):
        x0, x1, n = parse_data_head(ask(sock, f"CHAN{ch}:DATA:HEAD?"))
        data[ch] = np.frombuffer(query_binary_block(sock, f"CHAN{ch}:DATA?"), dtype="<f4")
        if len(data[ch]) != n:
            raise RuntimeError(f"CH{ch}: expected {n} points, received {len(data[ch])}")
        print(f"CH{ch} points: {len(data[ch])}", flush=True)

    # Write to a temporary name so that a partial file is never mistaken for a trace.
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    pd.DataFrame(
        {"t": np.linspace(x0, x1, n), "ch1": data[1], "ch2": data[2], "ch3": data[3]}
    ).to_csv(tmp_path, index=False, float_format="%.9g")
    tmp_path.replace(out_path)
    print(f"wrote {out_path}: {n} points", flush=True)


def _run_export(out_path, export):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with socket.create_connection((HOST, PORT), CONNECT_TIMEOUT) as s:
            s.settimeout(IO_TIMEOUT)
            print("IDN:", ask(s, "*IDN?"), flush=True)
            export(s, out_path)
    except Exception as exc:
        err_path = out_path.with_suffix(".txt")
        err_path.write_text(f"scope export failed: {exc!r}\n", encoding="utf-8")
        print(f"scope export failed; wrote diagnostic to {err_path}", flush=True)
        raise


def save_trace(out_path):
    """Save the acquisition that is currently in the scope's memory."""
    _run_export(out_path, fetch_and_write)


def arm_and_save(out_path, trigger_timeout=TRIGGER_TIMEOUT):
    """Arm a single acquisition, print ARMED, wait for it to finish, then save it."""

    def export(sock, path):
        write(sock, "*CLS")
        write(sock, "TRIG1:MODE NORM")  # AUTO would free-run without waiting for the shot
        ask(sock, "*OPC?")
        write(sock, "SING")
        write(sock, "*OPC?")  # answered once the single acquisition has completed
        time.sleep(ARM_SETTLE)
        print("ARMED", flush=True)
        sock.settimeout(trigger_timeout)
        try:
            read_line(sock)
        except socket.timeout:
            write(sock, "STOP")
            raise TimeoutError(f"no trigger on the scope within {trigger_timeout} s") from None
        sock.settimeout(IO_TIMEOUT)
        fetch_and_write(sock, path)

    _run_export(out_path, export)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--arm":
        arm_and_save(sys.argv[2])
    elif len(sys.argv) == 2:
        save_trace(sys.argv[1])
    else:
        sys.exit(__doc__)
