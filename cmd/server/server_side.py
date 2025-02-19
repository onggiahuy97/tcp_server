import socket
import time

class TCPServer:
    def __init__(self, host='localhost', port=12345):
        """Initialize server with host and port."""
        self.host = host
        self.port = port
        self.received_packets = set()
        self.total_received = 0
        self.total_expected = 0
        self.packet_count = 0
        
    def calculate_goodput(self):
        """Calculate goodput (received/sent packets ratio)."""
        if self.total_expected == 0:
            return 0
        return self.total_received / self.total_expected
        
    def start(self):
        """Start the server and listen for connections."""
        # Create TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Allow port reuse
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind socket to address
        server_socket.bind((self.host, self.port))
        
        # Listen for connections
        server_socket.listen(1)
        print(f"Server listening on {self.host}:{self.port}")
        
        while True:
            # Accept client connection
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")
            
            try:
                # Receive initial string
                initial_string = client_socket.recv(1024).decode()
                if initial_string.strip() == "network":
                    # Send success message
                    client_socket.send("success".encode())
                    
                    # Start receiving sequence numbers
                    while True:
                        # Receive sequence number
                        data = client_socket.recv(1024).decode()
                        if not data:
                            break
                            
                        # Parse sequence number
                        seq_num = int(data)
                        self.total_expected += 1
                        
                        # Track received packet
                        if seq_num not in self.received_packets:
                            self.received_packets.add(seq_num)
                            self.total_received += 1
                            self.packet_count += 1
                            
                        # Send ACK
                        ack = str(seq_num + 1)
                        client_socket.send(ack.encode())
                        
                        # Calculate and print goodput every 1000 packets
                        if self.packet_count >= 1000:
                            goodput = self.calculate_goodput()
                            print(f"Current goodput: {goodput:.4f}")
                            self.packet_count = 0
                            
            except Exception as e:
                print(f"Error: {e}")
            finally:
                client_socket.close()
                
if __name__ == "__main__":
    # Create and start server
    server = TCPServer()
    server.start()
