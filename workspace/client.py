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
        self.TOTAL_PACKETS = 5000
        self.WINDOW_SIZE = 4

        self.window = "" 
        self.seq_num = 0
        self.total_packets_sent = 0
        self.dropped_packets: List[int] = []
        self.recv_ack = 0
        
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
        return random.random() < 0.05

    def handle_retransmit(self):
        # Get first 4 elements of self.dropped_packets
        retransmit_seq = self.dropped_packets[:4]
        self.window = "RETRANSMIT "
        for res_seq in retransmit_seq:
            seq = ""
            if self.should_drop():
                seq = f"dropped"
                self.dropped_packets.append(res_seq)
            else:
                seq = res_seq

            self.window += f"{seq} "

        self.dropped_packets = self.dropped_packets[4:]

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
                self.seq_num = (self.seq_num + 1) % self.MAX_SEQ_NUM

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
            if self.total_packets_sent % 100 == 0:
                self.handle_retransmit()

            time.sleep(0.001)


        print("All sequences sent successfully")
        print(f"Dropped packets: {self.dropped_packets}")
        rate = (self.total_packets_sent - len(self.dropped_packets)) / self.TOTAL_PACKETS * 100
        print(f"Success rate: {rate}%")
        self.socket.close()

if __name__ == "__main__":
    client = Client(SERVER_IP, SERVER_PORT)
    if client.connect():
        client.send_data()
