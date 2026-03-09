#!/usr/bin/env python3
"""Patch tcp_split.rs to add warn log for missing flow deliveries."""
import re

path = "/opt/entrouter-line/src/edge/tcp_split.rs"
with open(path, "r") as f:
    src = f.read()

old = '''    /// Deliver incoming response data to the correct TCP client
    pub fn deliver(&self, flow_id: u32, data: Vec<u8>) {
        if let Some(sender) = self.active_flows.get(&flow_id) {
            let _ = sender.try_send(data);
        }
    }'''

new = '''    /// Deliver incoming response data to the correct TCP client
    pub fn deliver(&self, flow_id: u32, data: Vec<u8>) {
        if let Some(sender) = self.active_flows.get(&flow_id) {
            let _ = sender.try_send(data);
        } else {
            warn!(flow_id, bytes = data.len(), "no active flow — data dropped");
        }
    }'''

if old in src:
    src = src.replace(old, new)
    with open(path, "w") as f:
        f.write(src)
    print("PATCHED ok")
else:
    print("PATTERN NOT FOUND — checking current state:")
    # Show the deliver function
    for i, line in enumerate(src.split('\n'), 1):
        if 'deliver' in line.lower() or 'active_flow' in line.lower():
            print(f"  L{i}: {line}")
