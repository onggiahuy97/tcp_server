import socket 
import time 
import random 

SERVER_IP = "10.0.0.241"
SERVER_PORT = 8080

class Client: 
    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Sequence/window management
        self.MAX_SEQ_NUM = 2**16
        self.TOTAL_PACKETS = 1_000_000
        self.WINDOW_SIZE = 4
        self.base_seq = 0      # Start of the window
        self.next_seq_num = 0  # Next sequence to send
        self.total_sent = 0    # Track total packets sent

        self.dropped_packets = set()
        
    def connect(self): 
        self.socket.connect((self.server_ip, self.server_port))
        print("Connected to server")
        self.socket.sendall(b"network\n")
        response = self.socket.recv(1024).decode().strip()
        if response == "success":
            print("Handshake successful!")
            return True 
        else:
            print("Handshake failed!")
            return False 

    def should_drop_packet(self): 
        return random.random() < 0.01

    def send_data(self):
        while self.total_sent < self.TOTAL_PACKETS:
            # Calculate window boundaries with wraparound
            window_data = ""
            packets_in_window = 0 
            window_attempts = 0  # Add counter to prevent infinite loops
            
            # Try to fill window, but don't try forever
            while (packets_in_window < self.WINDOW_SIZE and 
                   self.total_sent < self.TOTAL_PACKETS and 
                   window_attempts < self.WINDOW_SIZE * 2):  # Allow some extra attempts
                
                seq = self.next_seq_num % self.MAX_SEQ_NUM
                window_attempts += 1
                
                if self.should_drop_packet():
                    self.dropped_packets.add(seq)
                    self.next_seq_num += 1
                    self.total_sent += 1
                    continue 
                    
                window_data += f"{seq}\n"
                self.next_seq_num += 1
                self.total_sent += 1
                packets_in_window += 1
            
            # If we got any packets to send
            if window_data:
                self.socket.sendall(window_data.encode())
                ack_response = self.socket.recv(1024).decode().strip()
                if ack_response.startswith("ACK"):
                    ack_num = int(ack_response.split()[1])
                    
                    if ack_num != self.base_seq:
                        old_base = self.base_seq % self.MAX_SEQ_NUM
                        self.base_seq = ack_num
                        # print(f"Window moved: {old_base} -> {ack_num % self.MAX_SEQ_NUM}")
                        # print(f"Drop rate: {len(self.dropped_packets) / self.total_sent * 100:.2f}%")
            # If entire window was dropped, still move forward
            else:
                self.base_seq = self.next_seq_num
                print(f"Entire window dropped, moving to next window")
            
            # Print progress periodically
            if self.total_sent % 10000 == 0:
                print(f"Progress: {self.total_sent}/{self.TOTAL_PACKETS} packets sent")

        self.socket.sendall(b"FIN\n")
        final_ack = self.socket.recv(1024).decode().strip()
        if final_ack == "FIN":
            print("Server finished receiving data")
                
        print("All sequences sent successfully")
        print(f"Final drop rate: {len(self.dropped_packets) / self.total_sent * 100:.2f}%")
        print(f"Total packets dropped: {len(self.dropped_packets)}")
        self.socket.close()
        

if __name__ == "__main__":
    client = Client(SERVER_IP, SERVER_PORT)
    if client.connect():
        client.send_data()
