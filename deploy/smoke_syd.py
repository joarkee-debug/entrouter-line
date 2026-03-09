import socket, time

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10.0)
sock.connect(('127.0.0.1', 8443))
print('SYD: Connected to 127.0.0.1:8443')
time.sleep(2)
sock.sendall(b'HELLO_FROM_SYDNEY\n')
print('SYD: Sent HELLO_FROM_SYDNEY')
try:
    data = sock.recv(4096)
    if data:
        print('SYD: RECEIVED:', repr(data))
    else:
        print('SYD: Connection closed, no data')
except Exception as e:
    print('SYD: Timeout/error:', str(e))
sock.close()
print('SYD: Done')
