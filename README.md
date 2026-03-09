# Entrouter Line

Zero-loss cross-region packet relay network.

XDP/eBPF kernel-bypass forwarding, adaptive FEC, multipath redundant transmission, and real-time latency-mesh routing.

## What This Does

Relays packets between globally distributed PoP (Point of Presence) nodes with:

- **Sub-microsecond forwarding** via XDP/eBPF (kernel bypass)
- **Zero observable packet loss** via adaptive Reed-Solomon FEC
- **Optimal routing** via real-time latency mesh (not BGP)
- **Instant connections** via QUIC 0-RTT + TCP splitting at edge
- **Always-encrypted** tunnels with ChaCha20-Poly1305

## Architecture

```
User → [QUIC 0-RTT] → Edge PoP → [UDP+FEC+Encrypted Tunnel] → Edge PoP → Origin
```

## Project Structure

```
src/
├── main.rs              # Entry point
├── config.rs            # Node & peer configuration
├── relay/               # Core relay engine
│   ├── tunnel.rs        # Encrypted UDP tunnels
│   ├── fec.rs           # Adaptive Forward Error Correction
│   └── forwarder.rs     # Packet forwarding (userspace → XDP)
├── mesh/                # Routing mesh
│   ├── probe.rs         # Latency probing
│   ├── router.rs        # Shortest-path routing
│   └── latency_matrix.rs
└── edge/                # Edge termination
    ├── tcp_split.rs     # TCP connection splitting
    └── quic_acceptor.rs # QUIC 0-RTT acceptor
```

## Build

```bash
cargo build --release
```

## License

MIT
