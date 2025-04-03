import socket
import random
import time
import logging

class PacketClient:
    def __init__(self, 
                # host="10.0.0.150", 
                host="localhost",  # Local testing
                port=5001, 
                max_packets=1_000_000,  # Increased to 10M
                max_seq=2**16, 
                window_size=50,  # Increased for throughput
                drop_prob=0.01,
                retry_delay=0.05,  # Reduced for speed
                transmit_delay=0.05):  # Minimized delay
        self.host = host
        self.port = port
        self.max_packets = max_packets
        self.max_seq = max_seq
        self.total_sent = 0
        self.window_size = window_size
        self.drop_prob = drop_prob
        self.current_seq = 0
        self.retry_delay = retry_delay
        self.transmit_delay = transmit_delay
        self.socket = None
        self.dropped = []
        self.wrap = 0
        self.last_ack = -1
        self.retransmissions = {1: 0, 2: 0, 3: 0, 4: 0}
        self.retransmission_counts = [0] * max_seq
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Optimize TCP settings
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)  # 1MB send buffer
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)  # 1MB receive buffer
            self.socket.connect((self.host, self.port))
            self.logger.info(f"Connected to {self.host}:{self.port}")

            self.socket.send(b'network\n')  # Send handshake message
            data = self.socket.recv(8).decode().strip()  # Receive handshake response
            if data == 'success':
                return True 

            return False

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise
    
    def should_drop(self):
        return random.random() <= self.drop_prob

    def handle_transmit(self):
        start = self.last_ack + 1
        block = f'{start}:'
        
        for i in range(self.window_size):
            should_drop = 0 if self.should_drop() else 1
            block += f'{should_drop}'

            if should_drop == 0:
                self.dropped.append(start + i)

        self.total_sent += self.window_size
        self.socket.send(block.encode())
        time.sleep(0.001)
        ack = int(self.socket.recv(8).decode())
        self.wrap += 1 if self.last_ack > ack else 0
        self.last_ack = ack

        self.logger.info(f"Last Ack: {self.last_ack}")

    def retransmit_block(self):
        pass

    def run(self):
        try:
            if self.connect():
                self.logger.info("Handshake established")
                while self.total_sent < self.max_packets:
                    self.handle_transmit()
            else:
                self.logger.info("Handshake failed")

            self.socket.send(f"finished".encode())
            self.logger.info("Finished")
            self.logger.info(f"Total sent: {self.total_sent} - total missing: {len(self.dropped)} - total wrap: {self.wrap}")
                
        except KeyboardInterrupt:
            self.logger.info("Client stopped by user")
        except Exception as e:
            self.logger.error(f"Error in client operation: {e}")
        finally:
            self.close()
    
    def close(self):
        if self.socket:
            self.socket.close()
            self.logger.info("Connection closed")
            self.socket = None


def main():
    client = PacketClient()
    client.run()


if __name__ == '__main__':
    main()
