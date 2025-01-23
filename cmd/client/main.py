# client.py
import socket
import random
import time

class TCPClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.window_size = 4
        self.base = 0
        self.next_seq_num = 0
        self.max_seq_num = 2**16
        self.dropped_packets = set()

    def send_packet(self, sock, seq_num):
        if random.random() < 0.01:  # 1% drop probability
            self.dropped_packets.add(seq_num)
            return False
        sock.send(str(seq_num).encode())
        return True

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))

            # Initial connection
            s.send("network".encode())
            response = s.recv(1024).decode()
            if response != "success":
                raise Exception("Connection failed")

            packets_sent = 0
            retransmission_counter = 0

            while packets_sent < 5000:
                # Send packets in current window
                while self.next_seq_num < self.base + self.window_size and packets_sent < 10_000_000:
                    seq_num = self.next_seq_num % self.max_seq_num
                    if self.send_packet(s, seq_num):
                        self.next_seq_num += 1
                    packets_sent += 1

                # Receive ACK
                try:
                    ack = int(s.recv(1024).decode())
                    self.base = ack
                except ValueError:
                    continue

                # Retransmit dropped packets every 100 sequence numbers
                retransmission_counter += 1
                if retransmission_counter >= 100:
                    for dropped_seq in self.dropped_packets.copy():
                        if self.send_packet(s, dropped_seq):
                            self.dropped_packets.remove(dropped_seq)
                    retransmission_counter = 0

                time.sleep(0.001)  # Small delay to prevent overwhelming the connection

if __name__ == "__main__":
    client = TCPClient()
    client.start()
