# server.py
import socket
import time
from collections import defaultdict

class TCPServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.received_packets = set()
        self.missing_packets = set()
        self.total_received = 0
        self.total_sent = 0
        self.goodput_measurements = []

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            print(f"Server listening on {self.host}:{self.port}")

            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                # Handle initial connection
                data = conn.recv(1024).decode()
                if data == "network":
                    conn.send("success".encode())

                while True:
                    try:
                        data = conn.recv(1024).decode()
                        if not data:
                            break

                        seq_num = int(data)
                        self.total_sent += 1
                        self.received_packets.add(seq_num)

                        # Check for missing packets
                        expected_packets = set(range(min(self.received_packets), max(self.received_packets) + 1))
                        self.missing_packets = expected_packets - self.received_packets

                        # Send ACK
                        ack = seq_num + 1
                        conn.send(str(ack).encode())

                        # Calculate goodput every 1000 packets
                        if len(self.received_packets) % 1000 == 0:
                            goodput = len(self.received_packets) / self.total_sent
                            self.goodput_measurements.append(goodput)
                            print(f"Current goodput: {goodput:.4f}")

                    except Exception as e:
                        print(f"Error: {e}")
                        break

if __name__ == "__main__":
    server = TCPServer()
    server.start()
