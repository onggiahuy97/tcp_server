import socket
import logging
import threading
import struct

class SequenceServer:
    def __init__(self, host='0.0.0.0', port=5001, window_size=1000, buffer_size=65536):
        self.host = host
        self.port = port
        self.window_size = window_size
        self.buffer_size = buffer_size  # Increased for better throughput
        self.server = None
        self.setup_logging()
        self.reset()
        self.ack_frequency = 500  # Send ACK every N packets
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def reset(self):
        self.total_recv = 0
        self.missing_numbers = set()
        self.current_seq = 0
        self.logger.info("Server state reset for new client")
    
    def setup(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)  # 1MB receive buffer
            self.server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle
            self.server.bind((self.host, self.port))
            self.server.listen(5)  # Increased backlog
            self.logger.info(f"Server listening on {self.host}:{self.port}")
        except OSError as e:
            self.logger.error(f"Socket setup error: {e}")
            raise
    
    def process_client_data(self, data, conn):
        """Process received data and update tracking, sending ACKs when needed"""
        try:
            decoded = data.decode()
            seqs = [seq for seq in decoded.split(",") if seq]
            
            needs_ack = False
            
            for seq in seqs:
                if seq.startswith('-'):
                    # Negative number indicates packet drop
                    try:
                        s = int(seq[1:])
                        self.missing_numbers.add(s)
                    except ValueError:
                        continue
                else:
                    try:
                        s = int(seq)
                        if s in self.missing_numbers:
                            self.missing_numbers.remove(s)
                    except ValueError:
                        continue
                
                self.total_recv += 1
                
                # Send ACK periodically
                if self.total_recv % self.ack_frequency == 0:
                    needs_ack = True
            
            # Send acknowledgment
            if needs_ack:
                try:
                    # Simple integer ACK - just send the count
                    ack_data = struct.pack("!Q", self.total_recv)
                    conn.sendall(ack_data)
                except Exception as e:
                    self.logger.error(f"Error sending ACK: {e}")

            if self.total_recv % 100000 == 0:
                self.logger.info(f"Received: {self.total_recv} packets, Missing: {len(self.missing_numbers)}")

        except Exception as e:
            self.logger.error(f"Error processing client data: {e}")
    
    def handle_client(self, conn, addr):
        self.logger.info(f"Connected by {addr}")
        self.reset()
        
        try:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)  # 1MB send buffer
            
            while True:
                data = conn.recv(self.buffer_size)
                if not data:
                    break
                
                self.process_client_data(data, conn)
        except ConnectionResetError:
            self.logger.warning(f"Connection reset by {addr}")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            conn.close()
            self.logger.info(f"Connection from {addr} closed")
            self.logger.info(f"Missing numbers count: {len(self.missing_numbers)}")
            self.logger.info("=" * 40)
    
    def run_threaded(self):
        self.setup()
        
        try:
            while True:
                conn, addr = self.server.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr)
                )
                client_thread.daemon = True
                client_thread.start()
        except KeyboardInterrupt:
            self.logger.info("Server shutting down...")
        finally:
            if self.server:
                self.server.close()
    
    def run(self):
        self.setup()
        
        try:
            while True:
                conn, addr = self.server.accept()
                self.handle_client(conn, addr)
        except KeyboardInterrupt:
            self.logger.info("Server shutting down...")
        finally:
            if self.server:
                self.server.close()

if __name__ == '__main__':
    server = SequenceServer()
    server.run_threaded()  # Changed to threaded mode by default
