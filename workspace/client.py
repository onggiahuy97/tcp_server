import socket 
import time 

SERVER_IP = "10.0.0.241"
SERVER_PORT = 8080

class Client: 
    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.base_seq = 0

    def connect(self): 
        self.socket.connect((self.server_ip, self.server_port))
        print("Connected to server")

        self.socket.sendall(b"network\n")
        response = self.socket.recv(1024).decode().strip()

        if response == "success":
            print("Handshake successfull!")
            return True 
        else:
            print("Handshake failed!")
            return False 

    def send_data(self):
        max_seq = 100 
        winddow_start = 0 

        while winddow_start < max_seq: 
            for i in range(4):
                seq_num = winddow_start + i 
                if seq_num >= max_seq:
                    break 

                self.socket.sendall(f"{seq_num}\n".encode())
                time.sleep(0.2)
            
            ack_response = self.socket.recv(1024).decode().strip()
            if ack_response.startswith("ACK"):
                ack_num = int(ack_response.split()[1])
                print(f"Received {ack_response}, sliding window")

                if ack_num > winddow_start:
                    winddow_start = ack_num

        print("All seq # sent successfully")
        self.socket.close()

if __name__ == "__main__":
    client = Client(SERVER_IP, SERVER_PORT)

    if client.connect():
        client.send_data()

