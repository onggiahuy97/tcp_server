import socket
import logging
import struct
import threading
import time

class Server:
    def __init__(self, host='0.0.0.0', port=5001, window_size=500, buffer_size=8192):
        self.host = host
        self.port = port
        self.window_size = window_size
        self.buffer_size = buffer_size  # Increased buffer size for better performance
        self.server = None
        self.total_recv = 0 
        self.missing_seqs = []
        self.max_seq = 2**16
        self.last_ack = 0
        self.start_time = time.time()
        self.seqs_over_time = []
        self.stop_goodput_timer = False
        self.goodput_thread = threading.Thread(target=self.goodput_timer, daemon=True)
        self.goodput_thread.start()
        self.setup_logging()

    @staticmethod
    def get_ip_address():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't need to be reachable
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def goodput_timer(self):
        while not self.stop_goodput_timer:
            time.sleep(2)
            self.record_data()
            self.print_goodput()
    
    def setup_logging(self):
        """Set up consistent logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def setup(self):
        """Set up and initialize the socket server"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # Keep connections alive
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
            self.server.bind((self.host, self.port))
            self.server.listen(1)  # Allow backlog of connections
            self.logger.info(f"Server listening on {self.host}:{self.port}")
        except OSError as e:
            self.logger.error(f"Socket setup error: {e}")
            raise

    def record_data(self):
        current_time = time.time() - self.start_time
        goodput = (self.total_recv) / (self.total_recv + len(self.missing_seqs)) if self.total_recv > 0 else 0
        self.seqs_over_time.append({
            'timestamp': current_time,
            'window_size': self.window_size,
            'received': self.total_recv - len(self.missing_seqs),
            'sent': self.total_recv,
            'missing': len(self.missing_seqs),
            'goodput': goodput
        })

    def print_goodput(self):
        if self.total_recv == 0:
            return
        goodput = (self.total_recv) / (self.total_recv + len(self.missing_seqs))
        self.logger.info(f"Recv: {self.total_recv} - Missing: {len(self.missing_seqs)} - Goodput: {goodput:.4f}")

    def process_client_data(self, data, conn):
        """Process received data and update tracking information"""
        try:
            # Add validation for data format
            decoded_data = data.decode()
            if ":" not in decoded_data:
                self.logger.error(f"Malformed data received: {decoded_data}")
                conn.send(f"{self.last_ack}".encode())
                return
                
            data = decoded_data.split(":")
            if len(data) < 2:
                self.logger.error(f"Split data has insufficient parts: {data}")
                conn.send(f"{self.last_ack}".encode())
                return
                
            start = int(data[0])
            binary = data[1]
            self.window_size = len(binary)
            count = 0

            for b in binary:
                seq = (start + count) % self.max_seq

                if b == '1':
                    self.last_ack = seq       
                    self.total_recv += 1
                elif b == '0':
                    self.missing_seqs.append(seq)
                else:
                    self.logger.warning(f"Unexpected character in binary string: {b}")
                count += 1

            conn.send(f"{self.last_ack}".encode())

        except Exception as e:
            self.logger.error(f"Error processing client data: {e}")
            # Send last known ack to keep connection alive
            conn.send(f"{self.last_ack}".encode())

    def process_client_retransmission(self, data, conn):
        try:
            binary_data = data[1:]
            if not binary_data:
                self.logger.warning("Received empty retransmission data")
                return
                
            n = len(binary_data) // 2 
            if n > 0:
                try:
                    actual_data = binary_data[:n*2]
                    seqs = struct.unpack(f"!{n}H", actual_data)
                    self.total_recv += len(seqs)
                    for seq in seqs:
                        if seq in self.missing_seqs:
                            self.missing_seqs.remove(seq)
                except struct.error as e:
                    self.logger.error(f"Unpacking error: {e}")
                    self.logger.debug(f"Raw data: {binary_data.hex()}")
            else:
                self.logger.warning("Received empty retransmission request")
        except Exception as e:
            self.logger.error(f"Error processing retransmission: {e}")

    def handshake(self, data, conn):
        """Perform handshake with the client"""
        data = data.decode().strip()  # Fixed decoding
        if data == 'network':
            conn.send(b'success\n')
            return True 
        return False

    def save_seq_data_to_file(self):
        """Save the sequence data to a CSV file"""
        try:
            import csv
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sequence_data_{timestamp}.csv"
            
            self.logger.info(f"Saving sequence data to {filename}")
            
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'window_size', 'received', 'sent', 'missing', 'goodput']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for data_point in self.seqs_over_time:
                    writer.writerow(data_point)
                    
            self.logger.info(f"Successfully saved {len(self.seqs_over_time)} data points")
        except Exception as e:
            self.logger.error(f"Error saving sequence data: {e}")

    def handle_client(self, conn, addr):
        """Handle a client connection"""
        self.logger.info(f"Connected by {addr}")
        
        try:
            # Optimize TCP performance
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            data = conn.recv(8)
            if self.handshake(data, conn):  # Pass data and conn to handshake
                self.logger.info("Handshake success")
                while True: 
                    data = conn.recv(1024)

                    if data[0] == ord('R'):
                        self.process_client_retransmission(data, conn)
                        continue
                    if data[0] == ord('F'):
                        self.logger.info("Finished")
                        break


                    self.process_client_data(data,conn)
            else:
                self.logger.warning("Handshake failed")
                return  # Exit early if handshake fails
            
        except ConnectionResetError:
            self.logger.warning(f"Connection reset by {addr}")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            conn.close()
            self.logger.info(f"Connection from {addr} closed")
            self.logger.info(f"Total packets received: {self.total_recv}")
            self.logger.info(f"Missing numbers count: {len(self.missing_seqs)}")
            self.save_seq_data_to_file()
            self.logger.info("=" * 40)
    
    def run(self):
        """Run server in single-client mode"""
        self.logger.info(f"Server IP address: {self.get_ip_address()}")

        self.setup()
        
        try:
            conn, addr = self.server.accept()
            self.handle_client(conn, addr)
        except Exception as e:
            self.logger.error(f"Error accepting connection: {e}")

        except KeyboardInterrupt:
            self.logger.info("Server shutting down...")
        finally:
            if self.server:
                self.server.close()

if __name__ == '__main__':
    server = Server()
    server.run()
