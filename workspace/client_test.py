import socket
import random
import time
import logging
import struct
import threading

class PacketClient:
    def __init__(self, 
                host="10.0.0.150", 
                port=5001, 
                max_packets=10_000_000,  # Increased to 10M
                max_seq=2**16, 
                window_size=1000,  # Increased for throughput
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
        self.dropped = set()
        self.wrap = 0
        self.retransmissions = {1: 0, 2: 0, 3: 0, 4: 0}
        self.retransmission_counts = [0] * max_seq
        self.last_ack = 0
        self.ack_lock = threading.Lock()
        
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
            
            # Start ACK listener thread
            self.ack_thread = threading.Thread(target=self.receive_acks)
            self.ack_thread.daemon = True
            self.ack_thread.start()
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise

    def receive_acks(self):
        """Thread to handle incoming acknowledgments from server"""
        try:
            while True:
                try:
                    # Receive ACK (8-byte unsigned long)
                    ack_data = self.socket.recv(8)
                    if not ack_data:
                        break
                    
                    if len(ack_data) == 8:
                        ack_value = struct.unpack("!Q", ack_data)[0]
                        with self.ack_lock:
                            self.last_ack = ack_value
                            
                        if ack_value % 100000 == 0:
                            self.logger.info(f"Received ACK for {ack_value} packets")
                except Exception as e:
                    self.logger.error(f"Error receiving ACK: {e}")
                    break
        except Exception as e:
            self.logger.error(f"ACK listener thread error: {e}")

    def generate_block(self):
        # Pre-allocate list for better performance
        block_items = []
        block_items_append = block_items.append  # Local reference for speed
        
        for _ in range(self.window_size):
            if random.random() <= self.drop_prob:
                self.dropped.add(self.current_seq)
                block_items_append(f"-{self.current_seq}")
            else:
                block_items_append(f"{self.current_seq}")

            self.current_seq += 1
            self.total_sent += 1

            if self.current_seq >= self.max_seq:
                self.current_seq = 0
                self.wrap += 1

        # Join all items at once - much more efficient
        return ','.join(block_items) + ','
    
    def retransmit_block(self):
        if not self.dropped:
            return

        # Make a copy to avoid set modification during iteration
        to_retry = list(self.dropped)
        if not to_retry:
            return
            
        # Take up to window_size packets for retransmission
        to_retry = to_retry[:self.window_size]
        block_items = []
        
        for seq in to_retry:
            if random.random() <= self.drop_prob:
                # Still dropping
                block_items.append(f"-{seq}")
                
                seq_index = seq % self.max_seq
                self.retransmission_counts[seq_index] += 1
                count = self.retransmission_counts[seq_index]
                if 1 <= count <= 4:
                    self.retransmissions[count] += 1
            else:
                # Successfully retransmitted
                block_items.append(f"{seq}")
                self.dropped.remove(seq)
        
        if block_items:
            block = ','.join(block_items) + ','
            try:
                self.socket.sendall(block.encode())
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
                # Periodically retransmit missing packets
                if self.total_sent % 5000 == 0:
                    self.retransmit_block()

                self.handle_send_packets()
                
                if self.total_sent % 100000 == 0:
                    with self.ack_lock:
                        ack_ratio = (self.last_ack / self.total_sent) * 100 if self.total_sent > 0 else 0
                    
                    self.logger.info(f"Sent {self.total_sent} packets, ACKed: {self.last_ack} ({ack_ratio:.2f}%), Missing: {len(self.dropped)}")

            # Final retransmissions to ensure delivery
            for _ in range(10):  # Try a few more times
                self.retransmit_block()
                time.sleep(0.1)
                
            self.logger.info(f"Final missing sequence numbers: {len(self.dropped)}")
            self.logger.info(f"Retransmission counts: {self.retransmissions}")
                
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
