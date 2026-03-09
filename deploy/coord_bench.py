#!/usr/bin/env python3
"""
Coordinate benchmark across London and Sydney VPS.
Launches both sides simultaneously via SSH, collects results.

Usage:
  python coord_bench.py --rate-mbps 50 --duration 10
  python coord_bench.py --rate-mbps 0 --duration 10  (full blast)
"""
import argparse
import subprocess
import threading
import time
import sys

LON_HOST = "root@YOUR_LONDON_IP"
SYD_HOST = "root@YOUR_SYDNEY_IP"
BENCH_CMD = "python3 /tmp/sync_bench.py"

def run_ssh(host, role, rate_mbps, duration, chunk_size, results, key):
    cmd = [
        "ssh", host,
        f"{BENCH_CMD} --role {role} --rate-mbps {rate_mbps} --duration {duration} --chunk-size {chunk_size}"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 60)
        results[key] = {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        results[key] = {"stdout": "", "stderr": "TIMEOUT", "returncode": -1}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rate-mbps", type=float, default=0)
    p.add_argument("--duration", type=float, default=10)
    p.add_argument("--chunk-size", type=int, default=1024)
    args = p.parse_args()

    print(f"=== Coordinated Benchmark: {args.rate_mbps} Mbps, {args.duration}s, {args.chunk_size}B chunks ===")
    results = {}

    # Start both sides simultaneously
    t_lon = threading.Thread(target=run_ssh, args=(LON_HOST, "sender", args.rate_mbps, args.duration, args.chunk_size, results, "london"))
    t_syd = threading.Thread(target=run_ssh, args=(SYD_HOST, "receiver", args.rate_mbps, args.duration, args.chunk_size, results, "sydney"))

    t_lon.start()
    t_syd.start()

    t_lon.join()
    t_syd.join()

    print("\n--- LONDON (sender) ---")
    if "london" in results:
        print(results["london"]["stdout"])
        if results["london"]["stderr"]:
            print(f"STDERR: {results['london']['stderr']}")
    else:
        print("NO RESULT")

    print("\n--- SYDNEY (receiver) ---")
    if "sydney" in results:
        print(results["sydney"]["stdout"])
        if results["sydney"]["stderr"]:
            print(f"STDERR: {results['sydney']['stderr']}")
    else:
        print("NO RESULT")

    # Parse SUMMARY lines
    for name, data in results.items():
        for line in data.get("stdout", "").split("\n"):
            if line.startswith("SUMMARY|"):
                print(f"\n{name.upper()}: {line}")

if __name__ == "__main__":
    main()
