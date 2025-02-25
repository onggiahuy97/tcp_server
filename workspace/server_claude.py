import socket
import time
import json
from typing import Optional, List, Dict

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
        self.last_ack = -1
        self.missing_seq: List[int] = []
        self.retransmit_seq: List[int] = []
        self.total_received = 0
        self.total_missing = 0
        
        # Data collection for graphs
        self.start_time = 0
        self.performance_data = []
        self.checkpoint_times = []
        self.goodput_values = []
        self.missing_packet_counts = []
        self.received_packet_counts = []
        
    def start(self): 
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        print(f"Server listening on port {self.port}...")
        
    def reset(self):
        self.expected_seq = 0
        self.last_ack = -1
        self.missing_seq = []
        self.total_received = 0
        self.total_missing = 0
        self.start_time = time.time()
        self.performance_data = []
        self.checkpoint_times = []
        self.goodput_values = []
        self.missing_packet_counts = []
        self.received_packet_counts = []
    
    def accept_connection(self) -> bool: 
        if self.socket == None: 
            print(f"Error: Server socket is not init")
            return False 
        try:
            self.reset()
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
    
    def save_performance_data(self):
        """Save performance data to a file for later graphing"""
        data = {
            "checkpoint_times": self.checkpoint_times,
            "goodput_values": self.goodput_values,
            "missing_packet_counts": self.missing_packet_counts,
            "received_packet_counts": self.received_packet_counts,
            "total_received": self.total_received,
            "total_missing": len(self.missing_seq),
            "final_goodput": self.goodput_values[-1] if self.goodput_values else 0
        }
        
        with open("tcp_performance_data.json", "w") as f:
            json.dump(data, f)
        print("Performance data saved to tcp_performance_data.json")
    
    def run(self): 
        if self.connection == None: 
            print(f"Error: No active connection")
            return
        try: 
            self.start_time = time.time()
            last_checkpoint = 0
            
            while True: 
                data = self.connection.recv(1024)
                if not data: 
                    break
                    
                message = data.decode().strip().split(" ")
                
                # Handle retransmissions differently
                if message[0] == "RETRANSMIT":
                    for seq in message[1:]:
                        if seq != "dropped" and int(seq) in self.missing_seq: 
                            self.missing_seq.remove(int(seq))
                            self.total_received += 1
                    print(f"Retransmitting: {message[1:]}")
                    continue
                
                # Track current expected sequence in the window
                current_seq = self.expected_seq
                
                # Process regular window packet by packet
                for seq in message:
                    if seq != "dropped":
                        seq_num = int(seq)
                        self.last_ack = seq_num
                        self.total_received += 1
                        current_seq = (seq_num + 1) % self.MAX_SEQ_NUM
                    else:
                        # Mark the current expected sequence as missing
                        self.missing_seq.append(current_seq)
                        self.total_missing += 1
                        current_seq = (current_seq + 1) % self.MAX_SEQ_NUM
                
                # Update expected sequence for next window
                self.expected_seq = (self.last_ack + 1) % self.MAX_SEQ_NUM
                
                # Send ACK for the last valid sequence received
                self.connection.sendall(str(f"ACK {self.last_ack}").encode())
                
                # Collect performance data every 1000 packets as per requirements
                if self.total_received // 1000 > last_checkpoint:
                    last_checkpoint = self.total_received // 1000
                    current_time = time.time() - self.start_time
                    
                    # Calculate goodput
                    goodput = (self.total_received / (self.total_received + len(self.missing_seq))) * 100
                    
                    # Store data points for graphing
                    self.checkpoint_times.append(current_time)
                    self.goodput_values.append(goodput)
                    self.missing_packet_counts.append(len(self.missing_seq))
                    self.received_packet_counts.append(self.total_received)
                    
                    print(f"Checkpoint {last_checkpoint}: Received: {self.total_received}, "
                          f"Missing: {len(self.missing_seq)}, Goodput: {goodput:.2f}%")
            
            # Final statistics
            print(f"Total received: {self.total_received}")
            print(f"Missing seq length: {len(self.missing_seq)}")
            if self.total_received > 0:
                goodput = self.total_received / (self.total_received + len(self.missing_seq)) * 100
                print(f"Final goodput: {goodput:.2f}%")
                
                # Add final data point
                current_time = time.time() - self.start_time
                self.checkpoint_times.append(current_time)
                self.goodput_values.append(goodput)
                self.missing_packet_counts.append(len(self.missing_seq))
                self.received_packet_counts.append(self.total_received)
            
            # Save data for graphing
            self.save_performance_data()
                
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
