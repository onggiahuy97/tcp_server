import socket
from typing import Optional, List 

DEFAULT_PORT = 8080
MAC_IP4_ADDR = "10.0.0.241"

class Server: 
    def __init__(self, host: str = '', port: int = DEFAULT_PORT):
        self.host = host 
        self.port = port 
        self.socket: Optional[socket.socket] = None 
        self.connection: Optional[socket.socket] = None 
        
        self.MAX_SEQ_NUM = 2**16
        self.WINDOW_SIZE = 4
        self.expected_seq = 0 
        self.recv_seq = set() 
        self.missing_seq = set() 
        self.current_window = []
        self.total_received = 0

    def start(self): 
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        print(f"Server listening on port {self.port}...")

    def accept_connection(self) -> bool: 
        if self.socket == None: 
            print(f"Error: Server socket is not init")
            return False 

        try:
            self.connection, addr = self.socket.accept()
            print(f"Accept connection from: {addr}")
            handshake = self.connection.recv(1024).decode().strip() 
            if handshake != "network":
                print(f"Handshake failed. Expected 'network', got: {handshake}")
                return False 
            self.connection.sendall(b"success\n")
            return True
        except Exception as e: 
            print(f"Connection error during handshake: {e}")
            return False 

    def is_continuous_window(self, window): 
        for i in range(len(window) - 1): 
            curr = window[i]
            next_seq = window[i + 1]
            if curr == self.MAX_SEQ_NUM - 1 and next_seq == 0:
                return False 
            elif (curr + 1) % self.MAX_SEQ_NUM != next_seq:
                return False 
        return True 

    def process_sequence(self, seq_num: int) -> None: 
        # Normalize sequence number
        seq_num = seq_num % self.MAX_SEQ_NUM 
        
        # Add to received sequences
        self.total_received += 1
        self.current_window.append(seq_num)

        # Only process when we have window size worth of sequences
        if len(self.current_window) == self.WINDOW_SIZE:
            # Sort window to check for continuous sequences
            self.current_window.sort()

            if self.current_window[0] > self.current_window[-1]:
                wrap_index = next(i for i in range(len(self.current_window) - 1) if self.current_window[i] > self.current_window[i + 1])
                self.current_window = (self.current_window[wrap_index + 1:] + self.current_window[:wrap_index + 1])
            
            if self.is_continuous_window(self.current_window):
                self.expected_seq = (self.current_window[-1] + 1) % self.MAX_SEQ_NUM

            
            # Clear window for next batch
            self.current_window = []
    
    def run(self): 
        if self.connection == None: 
            print(f"Error: No active connection")
            return

        try: 
            while True: 
                data = self.connection.recv(4096)
                if not data: 
                    print("No more data from client")
                    print(f"Total packets received: {self.total_received}/{1_000_000}")
                    break 

                message = data.decode().strip()

                if message == "FIN":
                    print("Received FIN, closing connection")
                    self.connection.sendall(b"FIN\n")
                    break
                
                sequences = message.split("\n")
                for seq_num in sequences:
                    seq_num = int(seq_num)
                    self.process_sequence(seq_num)
                
                # Only send ACK after processing complete window
                if len(self.current_window) == 0:
                    self.connection.sendall(f"ACK {self.expected_seq}\n".encode())
                
                if self.total_received % 10000 == 0:
                    print(f"Progress: {self.total_received} packets received")

        except Exception as e: 
            print(f"Error receiving data: {e}")
        finally: 
            if self.connection:
                self.connection.close()
                self.connection = None

if __name__ == "__main__":
    server = Server() 
    server.start()

    if server.accept_connection():
        server.run()
