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

    def start(self): 
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        print(f"Server listening on port {self.port}...")

    def process_sequence(self, seq_num: int) -> None: 
        # Normalize sequence number
        seq_num = seq_num % self.MAX_SEQ_NUM 
        
        # Add to received sequences
        self.recv_seq.add(seq_num)
        self.current_window.append(seq_num)

        # Only process when we have window size worth of sequences
        if len(self.current_window) == self.WINDOW_SIZE:
            # Sort window to check for continuous sequences
            self.current_window.sort()
            
            # If window starts with expected_seq and is continuous
            if (self.current_window[0] == self.expected_seq and 
                all(a + 1 == b for a, b in zip(self.current_window, self.current_window[1:]))):
                # Update expected_seq to next number after window
                self.expected_seq = (self.current_window[-1] + 1) % self.MAX_SEQ_NUM
            
            # Clear window for next batch
            self.current_window = []
    
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
    
    def run(self): 
        if self.connection == None: 
            print(f"Error: No active connection")
            return

        try: 
            while True: 
                data = self.connection.recv(1024)
                if not data: 
                    print(f"Client disconnected")
                    return 
                
                seq_num = int(data)
                print(f"Recv: {seq_num}")
                
                self.process_sequence(seq_num)
                
                # Only send ACK after processing complete window
                if len(self.current_window) == 0:
                    print(f"Sending ACK: {self.expected_seq}")
                    self.connection.sendall(f"ACK {self.expected_seq}\n".encode())
                
                print(f"Expected: {self.expected_seq}")
                
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
