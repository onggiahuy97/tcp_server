import socket
import random
import time
import logging
from typing import Optional
import struct

class PacketClient:
    def __init__(self, 
                # host="10.0.0.150", 
                host="localhost",  # Local testing
                port=5001, 
                max_packets= 10_000_000,  # Increased to 10M
                max_seq=2**16, 
                window_size=500,  # Increased for throughput
                drop_prob=0.01,
                transmit_delay=0.001):  # Minimized delay
        self.host = host
        self.port = port
        self.max_packets = max_packets
        self.max_seq = max_seq
        self.total_sent = 0
        self.window_size = window_size
        self.drop_prob = drop_prob
        self.current_seq = 0
        self.transmit_delay = transmit_delay
        self.socket = None
        self.dropped = []
        self.wrap = 0
        self.last_ack = -1
        self.last_retransmit_time = time.time()
        self.retransmit_interval = 2.0
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
        try:
            start = self.last_ack + 1
            block = f'{start}:'
            
            for i in range(self.window_size):
                should_drop = 0 if self.should_drop() else 1
                block += f'{should_drop}'

                if should_drop == 0:
                    self.dropped.append(start + i)

            self.total_sent += self.window_size
            self.socket.send(block.encode())
            time.sleep(self.transmit_delay)

            self.socket.settimeout(2.0)
            try:
                data = self.socket.recv(8).decode()
                if not data:
                    self.logger.warning("No data received, connection may be closed")
                    return
                ack = int(data)
                self.wrap += 1 if self.last_ack > ack else 0
                self.last_ack = ack

            except socket.timeout:
                self.logger.warning("Socket timeout, no ACK received")
                return 
            except ValueError as e:
                self.logger.error(f"Invalid ACK format: {e}")
                return 
            finally:
                self.socket.settimeout(None)

            current_time = time.time()
            if (current_time - self.last_retransmit_time >= self.retransmit_interval) and self.dropped:
                self.handle_retransmit()
                self.last_retransmit_time = current_time

            # self.logger.info(f"Last Ack: {self.last_ack} - Total sent: {self.total_sent}")
        except Exception as e:
            self.logger.error(f"Error in transmission: {e}")

    def handle_retransmit(self):
        if not self.dropped:
            self.logger.info("No packets to retransmit")
            return 

        seqs = self.dropped[:min(self.window_size, len(self.dropped))]
        block = []
        keep_drop = []
        for seq in seqs:
            normalized_seq = seq % self.max_seq
            self.retransmission_counts[normalized_seq] += 1
            count = min(self.retransmission_counts[normalized_seq], 4)
            self.retransmissions[count] += 1

            if self.should_drop():
                keep_drop.append(seq)
            else:
                block.append(normalized_seq) 

        self.total_sent += len(seqs)
        self.dropped = self.dropped[len(seqs):]        
        self.dropped.extend(keep_drop)

        if block:
            try: 
                binary_data = struct.pack(f"!{len(block)}H", *block)
                self.socket.send(b"R" + binary_data)
                time.sleep(self.transmit_delay)
                self.logger.info(f"Retransmitting {len(block)} sequences")
            except Exception as e:
                self.logger.error(f"Error in retransmission: {e}")
                self.logger.debug(f"Values causing error: {block}")


    def run(self):
        try:
            if self.connect():
                self.logger.info("Handshake established")

                while self.total_sent < self.max_packets:
                    self.handle_transmit()
                    
            else:
                self.logger.info("Handshake failed")

            self.socket.send(b"F")
            self.logger.info("Finished")
            self.logger.info(f"Total sent: {self.total_sent} - total missing: {len(self.dropped)} - total wrap: {self.wrap}")
            self.logger.info(f"Retransmissions: {self.retransmissions}")
            # self.logger.info(self.dropped)
                
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
