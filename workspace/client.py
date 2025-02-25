import socket 
import time 
import random
from typing import List

SERVER_IP = "localhost"
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

        self.window = "" 
        self.seq_num = 0
        self.total_packets_sent = 0
        self.dropped_packets: List[int] = []
        self.recv_ack = 0
        self.wrap = 0
        
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

    def should_drop(self):
        return random.random() < 0.01

    def handle_retransmit(self):
        # Process up to 4 dropped packets
        packets_to_process = min(self.WINDOW_SIZE, len(self.dropped_packets))
        if packets_to_process == 0:
            return
            
        retransmit_seq = self.dropped_packets[:packets_to_process]
        self.window = "RETRANSMIT "
        
        # Create a new list for packets that need to be re-added
        still_dropped = []
        
        for res_seq in retransmit_seq:
            if self.should_drop():
                seq = "dropped"
                still_dropped.append(res_seq)  # Re-add to dropped list
            else:
                seq = res_seq
                # Successfully transmitted
                
            self.window += f"{seq} "
        
        # Remove the processed packets and add back any still-dropped ones
        self.dropped_packets = self.dropped_packets[packets_to_process:] + still_dropped
        
        if len(self.window.split(" ")) > 1: 
            print(f"{self.window}")
        self.socket.sendall(self.window.encode())
        self.window = ""

    def send_data(self):
        while self.total_packets_sent < self.TOTAL_PACKETS:

            for _ in range(self.WINDOW_SIZE):
                seq = ""
                if self.should_drop():
                    seq = f"dropped"
                    self.dropped_packets.append(self.seq_num)
                else: 
                    seq = self.seq_num

                self.window += f"{seq} "

                self.seq_num = (self.seq_num + 1) 
                if self.seq_num == self.MAX_SEQ_NUM:
                    self.seq_num = 0
                    self.wrap += 1

            self.socket.sendall(self.window.encode())

            try :
                data = self.socket.recv(1024).decode().strip().split(" ")
                # sent_window = f"Sent window: {self.window}"
                # recv_text = f"-- Received: {data}"
                # print(f"{sent_window.ljust(50)} {recv_text.ljust(30)}")
                self.window = ""
                self.recv_ack = int(data[-1])
                # Either retranmit now or after 100 sequences

            except Exception as e: 
                print(f"Error receiving acks: {e}")
                break

            self.total_packets_sent += self.WINDOW_SIZE
            if self.total_packets_sent % 1000 == 0:
                self.handle_retransmit()

            # time.sleep(0.0001)


        print("All sequences sent successfully")
        print(f"Dropped packets length: {len(self.dropped_packets)}")
        rate = (self.total_packets_sent - len(self.dropped_packets)) / self.TOTAL_PACKETS * 100
        print(f"Success rate: {rate}%")
        print(f"Wrap arounds: {self.wrap}")
        self.socket.close()

if __name__ == "__main__":
    client = Client(SERVER_IP, SERVER_PORT)
    if client.connect():
        client.send_data()
