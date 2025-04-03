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
                transmit_delay=0.001):  # Minimized delay
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
        self.retransmissions = {1: 0, 2: 0, 3: 0, 4: 0}
        self.retransmission_counts = [0] * max_seq
        self.last_ack = 0
        
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

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise

    def generate_block(self):
        block = []
        
        for _ in range(self.window_size):
            if random.random() <= self.drop_prob:
                self.dropped.append(self.current_seq)
            else:
                block.append(self.current_seq)

            self.current_seq += 1
            self.total_sent += 1

            if self.current_seq >= self.max_seq:
                self.current_seq = 0
                self.wrap += 1

        return ','.join(map(str, block))
    
    def retransmit_block(self):
        if not self.dropped:
            return

        block = [] 
        seqs = self.dropped[:self.window_size]
        keep_dropped = []

        for seq in seqs:
            self.retransmission_counts[seq] += 1
            retry_count = min(4, self.retransmission_counts[seq])
            self.retransmissions[retry_count] += 1

            if random.random() <= self.drop_prob:
                # self.dropped.append(seq) 
                keep_dropped.append(seq)
            else:
                block.append(seq)

            self.total_sent += 1
        
        remaining_dropped = self.dropped[len(seqs):]
        self.dropped = keep_dropped + remaining_dropped

        # Only proceed if we have sequences to transmit
        if block:
            block_str = "r:" + ','.join(map(str, block))
            try:
                self.socket.sendall(block_str.encode())
                if self.transmit_delay > 0:
                    time.sleep(self.transmit_delay)
            except Exception as e:
                self.logger.error(f"Error during retransmission: {e}")

    def handle_send_packets(self):
        block = self.generate_block()
        try:
            self.socket.sendall(block.encode())
            # Only sleep if absolutely necessary - minimal delay
            if self.transmit_delay > 0:
                time.sleep(self.transmit_delay)
        except Exception as e:
            self.logger.error(f"Error during transmission: {e}")
    
    def run(self):
        try:
            self.connect()
            
            while self.total_sent < self.max_packets:
                self.handle_send_packets()

                if self.total_sent % 1000 == 0:
                    self.logger.info(f"Sent {self.total_sent} packets, Missing: {len(self.dropped)}")
                
            self.logger.info(f"Total packets sent: {self.total_sent}")
            self.logger.info(f"Total packets dropped: {len(self.dropped)}")
            self.logger.info(f"Packets retransmitted: {self.retransmissions}")
            self.logger.info(f"Wrap around count: {self.wrap}")
                
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
