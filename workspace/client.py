import socket 
import time 

SERVER_IP = "10.0.0.241"
SERVER_PORT = 8080

class Client: 
    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Sequence/window management
        self.MAX_SEQ_NUM = 2**16
        self.TOTAL_PACKETS = 10_000_000
        self.WINDOW_SIZE = 4
        self.base_seq = 0      # Start of the window
        self.next_seq_num = 0  # Next sequence to send
        
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

    def send_data(self):
        while self.base_seq < self.MAX_SEQ_NUM:
            # Send packets up to window size
            while (self.next_seq_num < self.base_seq + self.WINDOW_SIZE and 
                   self.next_seq_num < self.MAX_SEQ_NUM):
                print(f"Sending sequence number: {self.next_seq_num}")
                self.socket.sendall(f"{self.next_seq_num}\n".encode())
                self.next_seq_num += 1
                time.sleep(0.1)
            
            # Wait for ACK
            ack_response = self.socket.recv(1024).decode().strip()
            if ack_response.startswith("ACK"):
                ack_num = int(ack_response.split()[1])
                print(f"Received ACK: {ack_num}")
                
                if ack_num > self.base_seq:
                    print(f"Window moved: {self.base_seq} -> {ack_num}")
                    self.base_seq = ack_num
                    # Don't adjust next_seq_num here - it moves independently
            
        print("All sequences sent successfully")
        self.socket.close()

if __name__ == "__main__":
    client = Client(SERVER_IP, SERVER_PORT)
    if client.connect():
        client.send_data()
