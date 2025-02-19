# client.py
import socket
import random
import time

class TCPClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.window_size = 4  # Static window size
        self.sequence_number = 0
        self.max_sequence = 2**16
        self.drop_probability = 0.01
        self.dropped_packets = {}  # {seq_num: retransmission_count}

    def should_drop_packet(self):
        return random.random() < self.drop_probability

    def start(self, total_packets=1_000_000):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        packets_sent = 0
        retransmission_counter = 0

        try:
            # Connect and perform handshake
            print("Attempting to connect to server...")
            client_socket.connect((self.host, self.port))
            
            client_socket.send("network".encode())
            response = client_socket.recv(1024).decode().strip()
            
            if response != "success":
                raise Exception("Handshake failed")
            print("Connected successfully")

            # Main packet sending loop
            while packets_sent < total_packets:
                current_seq = self.sequence_number % self.max_sequence

                # Handle retransmissions every 100 packets
                if retransmission_counter >= 100:
                    self._handle_retransmission(client_socket)
                    retransmission_counter = 0

                # Regular packet sending
                if self.should_drop_packet():
                    print(f"Dropping packet {current_seq}")
                    self.dropped_packets[current_seq] = 1
                    retransmission_counter += 1
                else:
                    # Send packet: seq_num,window_size,is_retransmission
                    packet_info = f"{current_seq},{self.window_size},0"
                    client_socket.send(packet_info.encode())
                    
                    # Wait for ACK
                    try:
                        ack = int(client_socket.recv(1024).decode())
                    except:
                        print(f"Failed to receive ACK for {current_seq}")

                self.sequence_number += 1
                packets_sent += 1
                
                if packets_sent % 10000 == 0:
                    print(f"Progress: {packets_sent}/{total_packets} packets")

        except ConnectionRefusedError:
            print("Could not connect to server. Make sure server is running.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()
            print("Connection closed")

    def _handle_retransmission(self, client_socket):
        """Retransmit dropped packets."""
        packets_to_retransmit = list(self.dropped_packets.keys())
        
        for seq in packets_to_retransmit:
            retrans_count = self.dropped_packets[seq]
            
            # Limit to 4 retransmission attempts
            if retrans_count >= 4:
                print(f"Giving up on packet {seq} after {retrans_count} attempts")
                del self.dropped_packets[seq]
                continue

            if self.should_drop_packet():
                self.dropped_packets[seq] = retrans_count + 1
                print(f"Retransmission dropped again for packet {seq}")
                continue

            try:
                # Send packet with retransmission count
                packet_info = f"{seq},{self.window_size},{retrans_count}"
                client_socket.send(packet_info.encode())
                
                ack = int(client_socket.recv(1024).decode())
                if ack == (seq + 1) % self.max_sequence:
                    print(f"Successfully retransmitted packet {seq}")
                    del self.dropped_packets[seq]
                else:
                    self.dropped_packets[seq] = retrans_count + 1
            except:
                print(f"Failed to retransmit packet {seq}")
                self.dropped_packets[seq] = retrans_count + 1

if __name__ == "__main__":
    client = TCPClient()
    client.start()
