# server.py
import socket
import time
import matplotlib.pyplot as plt
import csv

class TCPServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.max_sequence = 2**16
        
        # For tracking packets and generating graphs
        self.received_packets = set()
        self.total_received = 0
        self.time_points = []
        self.seq_numbers = []
        self.window_sizes = []
        self.dropped_times = []
        self.dropped_seqs = []
        self.start_time = None
        self.retransmission_counts = {1: 0, 2: 0, 3: 0, 4: 0}

    def generate_graphs(self):
        # 1. TCP Window Size over time
        plt.figure(figsize=(10, 6))
        plt.plot(self.time_points, self.window_sizes)
        plt.title('TCP Sender and Receiver Window Size over Time')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Window Size')
        plt.savefig('window_size.png')
        plt.close()

        # 2. TCP Sequence numbers received
        plt.figure(figsize=(10, 6))
        plt.plot(self.time_points, self.seq_numbers)
        plt.title('TCP Sequence Numbers Received over Time')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Sequence Number')
        plt.savefig('seq_received.png')
        plt.close()

        # 3. TCP Sequence numbers dropped
        plt.figure(figsize=(10, 6))
        if self.dropped_seqs:
            plt.scatter(self.dropped_times, self.dropped_seqs, c='red', s=5)
        plt.title('TCP Sequence Numbers Dropped over Time')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Sequence Number')
        plt.savefig('seq_dropped.png')
        plt.close()


    def generate_retransmission_table(self):
        """Creates both CSV table and visual plot of retransmission data"""
        # Save to CSV
        with open('retransmission_table.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['# of retransmissions', '# of packets'])
            for retrans in range(1, 5):
                writer.writerow([retrans, self.retransmission_counts[retrans]])

        # Create visual plot of the table
        plt.figure(figsize=(10, 6))
        retrans_nums = list(range(1, 5))
        packet_counts = [self.retransmission_counts[i] for i in retrans_nums]
        
        # Create bar plot
        plt.bar(retrans_nums, packet_counts)
        plt.xlabel('Number of Retransmissions')
        plt.ylabel('Number of Packets')
        plt.title('Retransmission Statistics')
        
        # Add value labels on top of each bar
        for i in range(len(retrans_nums)):
            plt.text(retrans_nums[i], packet_counts[i], str(packet_counts[i]),
                    ha='center', va='bottom')
        
        # Set x-axis to show only whole numbers
        plt.xticks(retrans_nums)
        
        plt.savefig('retransmission_table.png')
        plt.close()

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(1)
        print(f"Server listening on {self.host}:{self.port}")

        self.start_time = time.time()

        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connected to {addr}")

            try:
                # Initial handshake
                initial_msg = client_socket.recv(1024).decode().strip()
                if initial_msg == "network":
                    client_socket.send("success".encode())
                    print("Handshake successful")

                    while True:
                        data = client_socket.recv(1024).decode()
                        if not data:
                            break

                        # Parse packet: seq_num,window_size,retransmission_count
                        seq_num, window_size, retrans_count = map(int, data.split(','))
                        current_time = time.time() - self.start_time

                        # Record data for graphs
                        self.time_points.append(current_time)
                        self.seq_numbers.append(seq_num)
                        self.window_sizes.append(window_size)

                        # Handle retransmissions
                        if retrans_count > 0:
                            self.retransmission_counts[retrans_count] += 1
                            self.dropped_times.append(current_time)
                            self.dropped_seqs.append(seq_num)

                        # Send ACK
                        ack = str((seq_num + 1) % self.max_sequence)
                        client_socket.send(ack.encode())

                        self.total_received += 1
                        if self.total_received % 1000 == 0:
                            print(f"Received {self.total_received} packets")
                            
            except Exception as e:
                print(f"Error: {e}")
            finally:
                client_socket.close()
                if self.total_received > 0:
                    self.generate_graphs()
                    self.generate_retransmission_table()
                    print("Generated output files")

if __name__ == "__main__":
    server = TCPServer()
    server.start()
