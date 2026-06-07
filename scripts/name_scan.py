#!/usr/bin/env python3
"""name_scan — check whether a project name is free across distribution channels.

Channels: PyPI · Crates.io · npm (unscoped) · Go module viability · GitHub
user/org · Homebrew core · domain availability (DNS query against 8.8.8.8).

Stdlib only; no installs. Examples:
    python3 name_scan.py taut
    python3 name_scan.py taut vyb tait --tlds com,dev,io,sh,ai
"""

from __future__ import annotations

import argparse
import os
import socket
import struct
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "name-scan/1.0 (+availability check)"}
AVAILABLE, TAKEN, UNKNOWN = "available", "taken", "unknown"
MARK = {AVAILABLE: "OK ", TAKEN: "XX ", UNKNOWN: "?? "}


def http_status(url: str, timeout: float) -> int | None:
    """Return HTTP status code, or None on network error."""
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def from_status(code: int | None, taken_codes=(200,), free_codes=(404, 410)) -> tuple[str, str]:
    if code in taken_codes:
        return TAKEN, f"HTTP {code}"
    if code in free_codes:
        return AVAILABLE, f"HTTP {code}"
    return UNKNOWN, f"HTTP {code}" if code else "no response"


def check_pypi(name, t):       return from_status(http_status(f"https://pypi.org/pypi/{name}/json", t))
def check_crates(name, t):     return from_status(http_status(f"https://crates.io/api/v1/crates/{name}", t))
def check_npm(name, t):        return from_status(http_status(f"https://registry.npmjs.org/{name}", t))
def check_github(name, t):     return from_status(http_status(f"https://api.github.com/users/{name}", t))
def check_homebrew(name, t):   return from_status(http_status(f"https://formulae.brew.sh/api/formula/{name}.json", t))


def check_go(name, t) -> tuple[str, str]:
    """Heuristic: is the canonical module path github.com/<name>/<name> published?
    Go has no central name registry — viability ≈ a free, short import path."""
    code = http_status(f"https://proxy.golang.org/github.com/{name}/{name}/@v/list", t)
    verdict, _ = from_status(code)
    return verdict, f"github.com/{name}/{name} ({'published' if verdict == TAKEN else 'free'})"


def dns_registered(domain: str, server: str, timeout: float) -> tuple[str, str]:
    """Query SOA for `domain` against `server` (default 8.8.8.8) over UDP/53.
    NXDOMAIN -> available; NOERROR (has SOA) -> taken. DNS-only heuristic."""
    header = os.urandom(2) + b"\x01\x00" + b"\x00\x01" + b"\x00\x00" * 3  # RD=1, qd=1
    question = b"".join(bytes([len(p)]) + p.encode() for p in domain.split(".")) + b"\x00"
    question += struct.pack(">HH", 6, 1)  # QTYPE=SOA, QCLASS=IN
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(header + question, (server, 53))
        resp, _ = sock.recvfrom(512)
    except Exception:
        return UNKNOWN, "dns timeout"
    finally:
        sock.close()
    if len(resp) < 4:
        return UNKNOWN, "short reply"
    rcode = resp[3] & 0x0F
    if rcode == 3:
        return AVAILABLE, "NXDOMAIN"
    if rcode == 0:
        return TAKEN, "has SOA"
    return UNKNOWN, f"rcode {rcode}"


def scan(name: str, tlds: list[str], dns_server: str, timeout: float) -> list[tuple[str, str, str]]:
    jobs = {
        "PyPI": lambda: check_pypi(name, timeout),
        "Crates.io": lambda: check_crates(name, timeout),
        "npm (unscoped)": lambda: check_npm(name, timeout),
        "Go module": lambda: check_go(name, timeout),
        "GitHub user/org": lambda: check_github(name, timeout),
        "Homebrew core": lambda: check_homebrew(name, timeout),
    }
    for tld in tlds:
        domain = f"{name}.{tld}"
        jobs[f"domain {domain}"] = (lambda d=domain: dns_registered(d, dns_server, timeout))

    rows: list[tuple[str, str, str]] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = {label: pool.submit(fn) for label, fn in jobs.items()}
        for label, fut in results.items():
            verdict, detail = fut.result()
            rows.append((label, verdict, detail))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan name availability across distribution channels.")
    ap.add_argument("names", nargs="+", help="candidate name(s) to check")
    ap.add_argument("--tlds", default="com,dev,io,sh", help="comma-separated TLDs (default: com,dev,io,sh)")
    ap.add_argument("--dns", default="8.8.8.8", help="DNS server for domain checks (default: 8.8.8.8)")
    ap.add_argument("--timeout", type=float, default=8.0, help="per-request timeout seconds (default: 8)")
    args = ap.parse_args()
    tlds = [t.strip() for t in args.tlds.split(",") if t.strip()]

    any_fully_clear = False
    for name in args.names:
        rows = scan(name, tlds, args.dns, args.timeout)
        width = max(len(label) for label, _, _ in rows)
        print(f"\n=== {name} ===")
        for label, verdict, detail in rows:
            print(f"  {MARK[verdict]} {label.ljust(width)}  {verdict:<9}  {detail}")
        taken = [label for label, v, _ in rows if v == TAKEN]
        clear = sum(1 for _, v, _ in rows if v == AVAILABLE)
        any_fully_clear = any_fully_clear or not taken
        verdict = "FULLY CLEAR" if not taken else f"taken: {', '.join(taken)}"
        print(f"  -> {clear}/{len(rows)} available  |  {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
