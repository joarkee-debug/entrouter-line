import socket, time

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10.0)
sock.connect(('127.0.0.1', 8443))
print('LON: Connected to 127.0.0.1:8443')
time.sleep(2)
sock.sendall(b'HELLO_FROM_LONDON\n')
print('LON: Sent HELLO_FROM_LONDON')
try:
    data = sock.recv(4096)
    if data:
        print('LON: RECEIVED:', repr(data))
    else:
        print('LON: Connection closed, no data')
except Exception as e:
    print('LON: Timeout/error:', str(e))
sock.close()
print('LON: Done')
