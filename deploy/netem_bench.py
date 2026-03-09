#!/usr/bin/env python3
"""
Run benchmark with simulated packet loss using tc netem.
Applies loss on both VPS, runs coord_bench, then removes loss.

Usage:
  python netem_bench.py --loss 1 --rate-mbps 100 --duration 10
"""
import argparse
import subprocess
import sys
import time

LON = "root@YOUR_LONDON_IP"
SYD = "root@YOUR_SYDNEY_IP"

def ssh(host, cmd, timeout=30):
    r = subprocess.run(["ssh", host, cmd], capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--loss", type=float, required=True, help="Packet loss percentage")
    p.add_argument("--rate-mbps", type=float, default=100)
    p.add_argument("--duration", type=float, default=10)
    p.add_argument("--chunk-size", type=int, default=4096)
    args = p.parse_args()

    print(f"=== Netem Loss Test: {args.loss}% loss, {args.rate_mbps} Mbps, {args.duration}s ===")

    # Restart relays to reset flow_id counters
    # Use systemd-run to launch relay as transient unit (survives SSH disconnect)
    print("Restarting relays...")
    ssh(LON, "systemctl stop entrouter-bench.service 2>/dev/null; fuser -k 4433/udp 2>/dev/null; fuser -k 8443/tcp 2>/dev/null; fuser -k 4434/udp 2>/dev/null; fuser -k 9090/tcp 2>/dev/null")
    ssh(SYD, "systemctl stop entrouter-bench.service 2>/dev/null; fuser -k 4433/udp 2>/dev/null; fuser -k 8443/tcp 2>/dev/null; fuser -k 4434/udp 2>/dev/null; fuser -k 9090/tcp 2>/dev/null")
    time.sleep(3)
    ssh(LON, "systemctl reset-failed entrouter-bench.service 2>/dev/null; systemd-run --no-block --unit=entrouter-bench -E RUST_LOG=info -p WorkingDirectory=/opt/entrouter-line /opt/entrouter-line/target/release/entrouter-line")
    ssh(SYD, "systemctl reset-failed entrouter-bench.service 2>/dev/null; systemd-run --no-block --unit=entrouter-bench -E RUST_LOG=info -p WorkingDirectory=/opt/entrouter-line /opt/entrouter-line/target/release/entrouter-line")
    time.sleep(4)
    # Verify relays are running
    out_lon, _, _ = ssh(LON, "systemctl is-active entrouter-bench.service")
    out_syd, _, _ = ssh(SYD, "systemctl is-active entrouter-bench.service")
    print(f"  London relay: {out_lon}, Sydney relay: {out_syd}")

    # Apply netem loss
    print(f"Applying {args.loss}% loss on both nodes...")
    ssh(LON, f"tc qdisc add dev enp1s0 root netem loss {args.loss}%")
    ssh(SYD, f"tc qdisc add dev enp1s0 root netem loss {args.loss}%")
    time.sleep(1)

    # Run benchmark
    print("Running benchmark...")
    try:
        r = subprocess.run(
            ["python", "deploy/coord_bench.py",
             "--rate-mbps", str(args.rate_mbps),
             "--duration", str(args.duration),
             "--chunk-size", str(args.chunk_size)],
            capture_output=True, text=True,
            timeout=args.duration + 60
        )
        print(r.stdout)
        if r.stderr:
            print(f"STDERR: {r.stderr}")
    finally:
        # ALWAYS remove netem
        print("Removing netem loss...")
        ssh(LON, "tc qdisc del dev enp1s0 root 2>/dev/null")
        ssh(SYD, "tc qdisc del dev enp1s0 root 2>/dev/null")
        # Stop relay units
        ssh(LON, "systemctl stop entrouter-bench.service 2>/dev/null")
        ssh(SYD, "systemctl stop entrouter-bench.service 2>/dev/null")
        print("Netem removed, relays stopped.")

if __name__ == "__main__":
    main()
