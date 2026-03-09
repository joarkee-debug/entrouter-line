/// Packet forwarder — userspace relay for now, XDP/eBPF upgrade later.
/// Receives packets on ingress, applies FEC encoding, sends through tunnel.
pub struct Forwarder;
