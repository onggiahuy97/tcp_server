import socket
import logging

class SequenceServer:
    def __init__(self, host='0.0.0.0', port=5001, window_size=32, buffer_size=8192):
        self.host = host
        self.port = port
        self.window_size = window_size
        self.buffer_size = buffer_size  # Increased buffer size for better performance
        self.server = None
        self.total_recv = 0 
        self.missing_seqs = []
        self.max_seq = 2**16
        self.setup_logging()
        self.reset()
    
    def setup_logging(self):
        """Set up consistent logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def reset(self):
        """Reset tracking variables when client disconnects"""
        self.total_recv = 0
        self.missing_seqs.clear()
        self.logger.info("Server state reset for new client")
    
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

    def find_missing_numbers(self, arr):
        if not arr:
            return []
        
        missing = []
        
        # Process each sorted segment
        i = 0
        while i < len(arr):
            # Find the end of current sorted segment
            segment_start = i
            while i + 1 < len(arr) and arr[i] < arr[i+1]:
                i += 1
            segment_end = i
            
            # Find missing numbers in this segment more efficiently
            # By using set difference instead of loop
            segment = arr[segment_start:segment_end+1]
            start, end = segment[0], segment[-1]
            expected = set(range(start, end + 1))
            segment_set = set(segment)
            missing.extend(sorted(expected - segment_set))
            
            # Move to start of next segment
            i += 1
        
        return missing
    def print_goodput(self):
        goodput = (self.total_recv) / (self.total_recv + len(self.missing_seqs))
        self.logger.info(f"Recv: {self.total_recv} - Missing: {len(self.missing_seqs)} - Goodput: {goodput:.4f}")


    def process_client_data(self, data, conn):
        """Process received data and update tracking information"""
        try:
            decoded = data.decode()

            if decoded.startswith("r"):
                seqs = list(map(int, filter(None, decoded.split(':')[1].split(','))))
                for seq in seqs:
                    self.total_recv += 1

                    if self.total_recv % 1000 == 0:
                        self.print_goodput()

                    if seq in self.missing_seqs:
                        self.missing_seqs.remove(seq)
                return

            seqs = list(map(int, filter(None, decoded.split(','))))
            missing = self.find_missing_numbers(seqs)

            for seq in seqs:
                self.total_recv += 1

                if self.total_recv % 1000 == 0:
                    self.print_goodput()

            self.missing_seqs.extend(missing)

        except Exception as e:
            self.logger.error(f"Error processing client data: {e}")

    
    def handle_client(self, conn, addr):
        """Handle a client connection"""
        self.logger.info(f"Connected by {addr}")
        self.reset()
        
        try:
            # Optimize TCP performance
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            while True:
                data = conn.recv(self.buffer_size)
                if not data:
                    self.logger.info("Client disconnected")
                    break
                self.process_client_data(data, conn)
        except ConnectionResetError:
            self.logger.warning(f"Connection reset by {addr}")
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            conn.close()
            self.logger.info(f"Connection from {addr} closed")
            self.logger.info(f"Total packets received: {self.total_recv}")
            self.logger.info(f"Missing numbers count: {len(self.missing_seqs)}")
            self.logger.info("=" * 40)
    
    def run(self):
        """Run server in single-client mode"""
        self.setup()
        
        try:
            while True:
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
    server = SequenceServer()
    server.run()
