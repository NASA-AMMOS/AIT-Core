import socket
import sys
import time

RATE = 1 # Do a little throttling so we dont completely thrash the server
BUFF_SIZE = 1024
TEST_DATA = b'U'*BUFF_SIZE
def main(mode,protocol,host,port):
    if mode == "server":
        if protocol == "TCP" or  protocol == "TCP-SEND":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((host, port))
            sock.listen()
            connection, address = sock.accept()
            with connection:
                if protocol == "TCP":
                    ts = time.time()
                    data_size = 0
                    while True:
                        buf = connection.recv(BUFF_SIZE)
                        data_size += len(buf)
                        te = time.time()
                        print(f"Received {data_size} bytes from {address} - est data rate: {data_size / (te-ts)}")
                else:
                    while True:
                        connection.sendall(TEST_DATA)
                        time.sleep(RATE)
        if protocol == "UDP":
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_socket.bind((host, port))
            ts = time.time()
            data_size = 0
            while True:
                buf, address = server_socket.recvfrom(BUFF_SIZE)
                data_size += len(buf)
                te = time.time()
                print(f"Received {data_size} bytes from {address} - est data rate: {data_size / (te-ts)}")
    if mode == "client":
        if protocol == "UDP":
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            while True:
                try:
                    print(f"Sent {len(TEST_DATA)} bytes to {host}:{port}")
                    sock.sendto(TEST_DATA, (host, port))
                    time.sleep(RATE)
                except Exception as e:
                    print(e)
                    continue
        if protocol == "TCP":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connected = False
            while not connected:
                try:
                    sock.connect((host, port))
                    connected = True
                except Exception as e:
                    print("retrying connection")
                    time.sleep(1)
            while True:
                try:
                    sock.send(TEST_DATA)
                    time.sleep(RATE)
                except Exception as e:
                    print(e)
                    continue

if __name__ == "__main__":
    print(sys.argv)
    mode = sys.argv[1]
    protocol = sys.argv[2]
    host = sys.argv[3]
    port = sys.argv[4]
    sys.exit(main(mode,protocol,host,int(port)))
