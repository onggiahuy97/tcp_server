import socket
import time
import random

class SlidingWindowClient:
    def __init__(self, window_size=4):
        self.window_size = window_size
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.unack_packets = {}  # Stores unacknowledged packets {seq_num: timestamp}
        self.next_seq = 1  # Next sequence number to send
        self.last_ack = 0  # Last acknowledged sequence
        self.MAX_SEQ = 2**16 - 1  # Maximum sequence number (as per project)
        self.PACKET_DROP_PROB = 0.1  # 10% packet drop probability

    def connect(self, host='localhost', port=8080):
        try:
            self.client.connect((host, port))
            print(f"Connected to server at {host}:{port}")

            # Handshake
            self.client.send("network\n".encode())
            response = self.client.recv(1024).decode().strip()

            if response == "success":
                print("Handshake successful. Starting transmission...")
                self.send_sequences()
            else:
                print(f"Handshake failed. Server responded: {response}")

        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            self.cleanup()

    def send_sequences(self):
        while self.next_seq < self.MAX_SEQ:
            # Send packets within window size
            while len(self.unack_packets) < self.window_size and self.next_seq <= self.MAX_SEQ:
                if random.random() > self.PACKET_DROP_PROB:  # Simulating packet drop
                    self.client.send(f"SEQ {self.next_seq}\n".encode())
                    print(f"Sending: SEQ {self.next_seq}")

                self.unack_packets[self.next_seq] = time.time()  # Store time sent
                self.next_seq += 1  # Increment sequence number

            # Process ACKs
            try:
                self.client.settimeout(1)  # 1-second timeout for ACK
                ack = self.client.recv(1024).decode().strip()
                ack_seq = int(ack.split(" ")[1])  # Extract ACK number
                print(f"Received ACK: {ack_seq}")

                # Remove all acknowledged packets from the buffer
                keys_to_remove = [seq for seq in self.unack_packets.keys() if seq <= ack_seq]
                for seq in keys_to_remove:
                    del self.unack_packets[seq]

                # Slide window if all within window are acknowledged
                if len(self.unack_packets) == 0:
                    print("Sliding window forward...")

            except socket.timeout:
                print("Timeout: Retransmitting lost packets...")
                for seq in list(self.unack_packets.keys()):
                    self.client.send(f"SEQ {seq}\n".encode())
                    print(f"Retransmitting: SEQ {seq}")

    def cleanup(self):
        try:
            self.client.send("finish\n".encode())
            response = self.client.recv(1024).decode().strip()
            if response == "goodbye":
                print("Server acknowledged finish")
        except:
            pass
        finally:
            self.client.close()
            print("Connection closed")

if __name__ == "__main__":
    try:
        client = SlidingWindowClient(window_size=4)
        client.connect()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")

