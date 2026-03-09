/// TCP connection splitter at the edge.
/// ACKs user immediately (low RTT), buffers and relays over the fast tunnel.
pub struct TcpSplitter;
