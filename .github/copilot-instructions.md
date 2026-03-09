# Entrouter Line — AI Instructions

## Project Overview

**Entrouter Line** is a zero-loss cross-region packet relay network written in **Rust**.

This is a **separate project** from entropy-core / entropy-router. Do NOT mix them up.

## Architecture

- **Relay layer** (`src/relay/`): Encrypted UDP tunnels between PoPs, FEC encoding, packet forwarding
- **Mesh layer** (`src/mesh/`): Latency probing, real-time routing, latency matrix
- **Edge layer** (`src/edge/`): TCP splitting, QUIC 0-RTT termination
- **Config** (`src/config.rs`): Node configuration, peer discovery

## Key Technologies

| Component | Implementation |
|---|---|
| Packet forwarding | Userspace initially, XDP/eBPF (`aya`) later |
| Inter-PoP protocol | UDP + ChaCha20-Poly1305 encryption |
| Loss recovery | Adaptive Reed-Solomon FEC |
| Transport | QUIC via `quinn` |
| Async runtime | Tokio |
| Routing | Dijkstra on live latency matrix |

## Rules

- **Language:** Rust (edition 2021), always
- **No Node.js/TypeScript server code** — this is pure Rust
- **No mixing with entropy-core** — separate project, separate binary, separate deployment
- **Performance first** — hot path must be zero-copy where possible
- **eBPF code** uses the `aya` framework (Rust-native), not C
- **Encryption** is always on between PoPs — ChaCha20-Poly1305 with pre-shared keys
- **FEC** is adaptive — parity ratio adjusts to measured loss rate per-path

## Build

```bash
cargo build --release
```

## Deploy Target

Vultr VPS instances across multiple regions (Sydney, London, Singapore, etc.)
