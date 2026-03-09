"""Simple relay test: connect to local TCP edge, send 100 chunks of 1KB, measure what arrives."""
import socket, time, sys, struct

HOST = '127.0.0.1'
PORT = 8443
LABEL = sys.argv[1] if len(sys.argv) > 1 else 'NODE'

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.connect((HOST, PORT))
print(f'[{LABEL}] connected')

# Send 100 x 1KB chunks with seq numbers, 10ms apart
total_sent = 0
for i in range(100):
    data = struct.pack('<I', i) + b'X' * 1020
    sock.sendall(data)
    total_sent += 1024
    time.sleep(0.01)

print(f'[{LABEL}] sent {total_sent} bytes ({total_sent//1024} chunks)')

# Now receive for 10 seconds
sock.settimeout(10.0)
rx_bytes = 0
rx_chunks = 0
try:
    while True:
        data = sock.recv(65536)
        if not data:
            break
        rx_bytes += len(data)
        rx_chunks += 1
except socket.timeout:
    pass

print(f'[{LABEL}] received {rx_bytes} bytes in {rx_chunks} recvs')
sock.close()
print(f'[{LABEL}] done')
