import socket
import time

class SimpleWindowClient:
    def __init__(self, window_size=4):
        self.window_size = window_size
        self.sequence = 0  # Current sequence number
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def connect(self, host='localhost', port=8080):
        try:
            # Connect and perform handshake
            self.client.connect((host, port))
            print(f"Connected to server at {host}:{port}")
            
            self.client.send("network\n".encode())
            response = self.client.recv(1024).decode().strip()
            
            if response == "success":
                print("Handshake successful. Starting transmission...")
                self.send_sequences()
            else:
                print(f"Handshake failed. Server responded: {response}")
                
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            self.cleanup()
            
    def send_sequences(self):
        try:
            while True:  # Keep sending sequences until interrupted
                # Send window_size number of sequences
                for _ in range(self.window_size):
                    message = f"SEQ {self.sequence}\n"
                    print(f"Sending: {message.strip()}")
                    self.client.send(message.encode())
                    self.sequence += 1
                    time.sleep(0.5)  # Small delay between sequences
                
        except KeyboardInterrupt:
            print("\nTransmission interrupted by user")
            
    def cleanup(self):
        try:
            self.client.send("finish\n".encode())
            response = self.client.recv(1024).decode().strip()
            if response == "goodbye":
                print("Server acknowledged finish")
        except:
            pass
        finally:
            self.client.close()
            print("Connection closed")

if __name__ == "__main__":
    try:
        client = SimpleWindowClient(window_size=4)
        client.connect()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
