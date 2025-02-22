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
        self.expected_seq = 0

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
    
    def run(self): 
        if self.connection == None: 
            print(f"Error: No active connection")
            return

        sequences: List[int] = [] 

        try: 
            while True: 
                data = self.connection.recv(1024)
                if not data: 
                    print(f"Client disconnected")
                    return 
                seq_num = int(data)
                print(f"Recv: {seq_num}\n")
                sequences.append(seq_num)

                if seq_num == self.expected_seq:
                    self.expected_seq += 1

                self.connection.sendall(f"ACK {self.expected_seq}\n".encode())
                print(f"Send ACK: {self.expected_seq}")


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
