import socket
from typing import Optional, List 

DEFAULT_PORT = 8080
MAC_IP4_ADDR = "localhost"

class Server: 
    def __init__(self, host: str = '', port: int = DEFAULT_PORT):
        self.host = host 
        self.port = port 
        self.socket: Optional[socket.socket] = None 
        self.connection: Optional[socket.socket] = None 
        
        self.MAX_SEQ_NUM = 2**16
        self.WINDOW_SIZE = 4
        self.expected_seq = 0 
        self.last_ack = 0

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

        try: 
            while True: 
                data = self.connection.recv(1024)
                if not data: 
                    break 

                message = data.decode().strip().split(" ")

                for seq in message:
                    if seq != "dropped":
                        self.last_ack = int(seq) 
                    else: 
                        break 

                print(f"Received message: {message} --- Last ack: {self.last_ack}")

                self.connection.sendall(str(f"ACK {self.last_ack}").encode())
                
        except Exception as e: 
            print(f"Error receiving data: {e}")
        finally: 
            if self.connection:
                self.connection.close()
                self.connection = None

if __name__ == "__main__":
    server = Server() 
    server.start()

    while True: 
        if server.accept_connection(): 
            server.run() 
