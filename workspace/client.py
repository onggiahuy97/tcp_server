import socket 
import time 
import random

SERVER_IP = "localhost"
SERVER_PORT = 8080

class Client: 
    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Sequence/window management
        self.MAX_SEQ_NUM = 2**16
        self.TOTAL_PACKETS = 100
        self.WINDOW_SIZE = 4

        self.window = "" 
        self.seq_num = 0
        self.total_packets_sent = 0
        self.dropped_packets = []
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
        return random.random() < 0.1

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

            self.total_packets_sent += self.WINDOW_SIZE
            time.sleep(0.01)

            try :
                data = self.socket.recv(1024).decode().strip().split(" ")
                print(f"Sent window: {self.window}\t\t -- Received: {data}")
                self.window = ""
                self.recv_ack = int(data[-1])
                self.seq_num = self.recv_ack
            except Exception as e: 
                print(f"Error receiving acks: {e}")
                break



        print("All sequences sent successfully")
        self.socket.close()

if __name__ == "__main__":
    client = Client(SERVER_IP, SERVER_PORT)
    if client.connect():
        client.send_data()
