/// Packet forwarder — central routing engine for the relay mesh.
/// Receives packets from all tunnels, routes to destination or delivers locally.
/// Supports multi-hop forwarding via mesh router's shortest-path algorithm.
use std::sync::Arc;

use dashmap::DashMap;
use tokio::sync::mpsc;
use tracing::{debug, info, warn};

use crate::mesh::probe::Prober;
use crate::mesh::router::MeshRouter;
use crate::relay::tunnel::{ReceivedPacket, Tunnel};
use crate::relay::wire;

/// Traffic delivered to the local edge (this node is the destination)
pub struct LocalDelivery {
    pub flow_id: u32,
    pub data: Vec<u8>,
    pub source_node: String,
}

#[derive(Debug)]
pub enum ForwarderError {
    NoRoute(String),
    SendFailed(std::io::Error),
    NoTunnel(String),
}

impl std::fmt::Display for ForwarderError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoRoute(dest) => write!(f, "no route to {dest}"),
            Self::SendFailed(e) => write!(f, "send failed: {e}"),
            Self::NoTunnel(peer) => write!(f, "no tunnel to peer {peer}"),
        }
    }
}

pub struct Forwarder {
    node_id: String,
    router: Arc<MeshRouter>,
    prober: Arc<Prober>,
    tunnels: DashMap<String, Arc<Tunnel>>,
    local_tx: mpsc::Sender<LocalDelivery>,
}

impl Forwarder {
    pub fn new(
        node_id: String,
        router: Arc<MeshRouter>,
        prober: Arc<Prober>,
        local_tx: mpsc::Sender<LocalDelivery>,
    ) -> Self {
        Self {
            node_id,
            router,
            prober,
            tunnels: DashMap::new(),
            local_tx,
        }
    }

    pub fn add_tunnel(&self, peer_id: String, tunnel: Arc<Tunnel>) {
        self.tunnels.insert(peer_id, tunnel);
    }

    /// Process an inbound packet from a peer's receive loop
    pub async fn handle_inbound(&self, from_peer: &str, packet: ReceivedPacket) {
        match packet.packet_type {
            wire::PACKET_PING => {
                let pong = Prober::create_pong(&packet.payload);
                if let Some(tunnel) = self.tunnels.get(from_peer) {
                    if let Err(e) = tunnel.send(wire::PACKET_PONG, &pong).await {
                        warn!(peer = %from_peer, "pong send failed: {e}");
                    }
                }
            }
            wire::PACKET_PONG => {
                self.prober.handle_pong(from_peer, &packet.payload);
            }
            wire::PACKET_DATA | wire::PACKET_PARITY => {
                self.route_data(from_peer, &packet.payload).await;
            }
            wire::PACKET_CONTROL => {
                debug!(from = %from_peer, "control packet received");
            }
            _ => {
                warn!(ptype = packet.packet_type, "unknown packet type");
            }
        }
    }

    /// Route a data packet to its destination
    async fn route_data(&self, from_peer: &str, payload: &[u8]) {
        let Some((flow_id, dest_node, data)) = decode_relay_header(payload) else {
            warn!("invalid relay header");
            return;
        };

        if dest_node == self.node_id {
            let delivery = LocalDelivery {
                flow_id,
                data: data.to_vec(),
                source_node: from_peer.to_string(),
            };
            if self.local_tx.send(delivery).await.is_err() {
                warn!("local delivery channel closed");
            }
        } else {
            if let Err(e) = self.forward_to(dest_node, payload).await {
                warn!(dest = %dest_node, "forward failed: {e}");
            }
        }
    }

    /// Send data to a destination node (called by local edge for outbound traffic)
    pub async fn send_to_node(
        &self,
        dest_node: &str,
        flow_id: u32,
        data: &[u8],
    ) -> Result<(), ForwarderError> {
        let payload = encode_relay_header(flow_id, dest_node, data);
        self.forward_to(dest_node, &payload).await
    }

    /// Forward a relay payload to the next hop toward destination
    async fn forward_to(&self, dest_node: &str, relay_payload: &[u8]) -> Result<(), ForwarderError> {
        let route = self
            .router
            .next_hop(dest_node)
            .ok_or_else(|| ForwarderError::NoRoute(dest_node.to_string()))?;

        let tunnel = self
            .tunnels
            .get(&route.next_hop)
            .ok_or_else(|| ForwarderError::NoTunnel(route.next_hop.clone()))?;

        tunnel
            .send(wire::PACKET_DATA, relay_payload)
            .await
            .map_err(ForwarderError::SendFailed)
    }

    /// Run the main forwarding loop — receives from all peer receive loops
    pub async fn run(self: Arc<Self>, mut rx: mpsc::Receiver<(String, ReceivedPacket)>) {
        info!(node = %self.node_id, "forwarder started");
        while let Some((from_peer, packet)) = rx.recv().await {
            self.handle_inbound(&from_peer, packet).await;
        }
        info!("forwarder stopped");
    }

    pub fn node_id(&self) -> &str {
        &self.node_id
    }

    pub fn peer_count(&self) -> usize {
        self.tunnels.len()
    }
}

// --- Relay header encoding/decoding ---
// Layout: [4 bytes flow_id LE] [1 byte dest_len] [N bytes dest_node UTF-8] [rest: data]

pub fn encode_relay_header(flow_id: u32, dest_node: &str, data: &[u8]) -> Vec<u8> {
    let dest_bytes = dest_node.as_bytes();
    let dest_len = dest_bytes.len().min(255) as u8;
    let mut buf = Vec::with_capacity(5 + dest_len as usize + data.len());
    buf.extend_from_slice(&flow_id.to_le_bytes());
    buf.push(dest_len);
    buf.extend_from_slice(&dest_bytes[..dest_len as usize]);
    buf.extend_from_slice(data);
    buf
}

pub fn decode_relay_header(buf: &[u8]) -> Option<(u32, &str, &[u8])> {
    if buf.len() < 5 {
        return None;
    }
    let flow_id = u32::from_le_bytes([buf[0], buf[1], buf[2], buf[3]]);
    let dest_len = buf[4] as usize;
    if buf.len() < 5 + dest_len {
        return None;
    }
    let dest_node = std::str::from_utf8(&buf[5..5 + dest_len]).ok()?;
    let data = &buf[5 + dest_len..];
    Some((flow_id, dest_node, data))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn relay_header_roundtrip() {
        let data = b"hello world";
        let encoded = encode_relay_header(42, "syd-01", data);
        let (flow_id, dest, payload) = decode_relay_header(&encoded).unwrap();
        assert_eq!(flow_id, 42);
        assert_eq!(dest, "syd-01");
        assert_eq!(payload, data);
    }

    #[test]
    fn relay_header_empty_data() {
        let encoded = encode_relay_header(0, "lon", &[]);
        let (flow_id, dest, payload) = decode_relay_header(&encoded).unwrap();
        assert_eq!(flow_id, 0);
        assert_eq!(dest, "lon");
        assert!(payload.is_empty());
    }

    #[test]
    fn relay_header_too_short() {
        assert!(decode_relay_header(&[0, 1, 2]).is_none());
    }
}
