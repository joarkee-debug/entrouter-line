use serde::Deserialize;
use std::net::SocketAddr;

#[derive(Debug, Deserialize)]
pub struct Config {
    /// This node's unique identifier
    pub node_id: String,
    /// Region label (e.g. "syd", "lon", "sgp")
    pub region: String,
    /// Address to listen on for incoming relay traffic
    pub listen_addr: SocketAddr,
    /// Known peer PoP nodes
    pub peers: Vec<PeerConfig>,
}

#[derive(Debug, Deserialize)]
pub struct PeerConfig {
    pub node_id: String,
    pub region: String,
    pub addr: SocketAddr,
}
