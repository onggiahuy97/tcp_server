import socket 
import time 
import random
from typing import List, Dict
import json

SERVER_IP = "10.0.0.150"
SERVER_PORT = 8080

class Client: 
    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Sequence/window management
        self.MAX_SEQ_NUM = 2**16
        self.TOTAL_PACKETS = 1000
        self.WINDOW_SIZE = 4

        self.window = "" 
        self.seq_num = 0
        self.total_packets_sent = 0
        self.total_packets_acked = 0
        self.dropped_packets: List[int] = []
        self.recv_ack = 0
        self.wrap = 0

        # Performance tracking 
        self.start_time = 0 
        self.last_report_time = 0 
        self.last_report_packets = 0

        # Retransmission tracking 
        self.retransmission_counts: Dict[int, int] = {} 
        self.window_size_over_time = []
        self.sequence_received_over_time = []
        self.sequence_dropped_over_time = []
        self.time_checkpoints = []
        
    def connect(self): 
        self.socket.connect((self.server_ip, self.server_port))
        print("Connected to server")
        self.socket.sendall(b"network\n")
        response = self.socket.recv(1024).decode().strip()
        if response == "success":
            print("Handshake successful!")
            return True 
        else:
            print("Handshake failed!")
            return False 

    def should_drop(self):
        return random.random() < 0.01

    def handle_retransmit(self):
        print(f"Dropped packets: {self.dropped_packets}")
        # Process up to 4 dropped packets
        packets_to_process = min(self.WINDOW_SIZE, len(self.dropped_packets))
        if packets_to_process == 0:
            return
            
        retransmit_seq = self.dropped_packets[:packets_to_process]
        self.window = "RETRANSMIT "
        
        # Create a new list for packets that need to be re-added
        still_dropped = []
        
        for res_seq in retransmit_seq:
            if res_seq in self.retransmission_counts:
                self.retransmission_counts[res_seq] += 1
            else: 
                self.retransmission_counts[res_seq] = 1 

            if self.should_drop():
                seq = "dropped"
                still_dropped.append(res_seq)  # Re-add to dropped list
            else:
                seq = res_seq
                # Successfully transmitted
                
            self.window += f"{seq} "
        
        # Remove the processed packets and add back any still-dropped ones
        self.dropped_packets = self.dropped_packets[packets_to_process:] + still_dropped
        
        if len(self.window.split(" ")) > 1: 
            print(f"{self.window}")
        self.socket.sendall(self.window.encode())
        print(f"Retransmitted {packets_to_process} packets")
        self.window = ""

    def record_checkpoint(self):
        current_time = time.time() - self.start_time

        self.time_checkpoints.append(current_time) 
        self.window_size_over_time.append(self.WINDOW_SIZE)
        self.sequence_received_over_time.append(self.total_packets_acked)
        self.sequence_dropped_over_time.append(len(self.dropped_packets))

    def save_performance_data(self):
        retrans_stats = {1: 0, 2: 0, 3: 0, 4: 0}
        for seq, count in self.retransmission_counts.items():
            if 1 <= count <= 4:
                retrans_stats[count] += 1 
            else: 
                retrans_stats[4] += 1

        data = {
            "checkpoint_times": self.time_checkpoints,
            "window_sizes": self.window_size_over_time,
            "sequence_received": self.sequence_received_over_time,
            "sequence_dropped": self.sequence_dropped_over_time,
            "retransmission_counts": [
                retrans_stats[1],
                retrans_stats[2],
                retrans_stats[3],
                retrans_stats[4]
            ],
            "total_sent": self.total_packets_sent,
            "total_acked": self.total_packets_acked,
            "total_dropped": len(self.dropped_packets)
        }

        with open("client_performance_data.json", "w") as f: 
            json.dump(data, f)
        print("Performance data saved")

    def report_statistics(self, force=False):
        now = time.time()
        # Record data point for graphs
        self.record_checkpoint()
        
        # Report every 10 seconds or if forced
        if force or (now - self.last_report_time >= 10):
            elapsed = now - self.start_time
            packets_since_last = self.total_packets_sent - self.last_report_packets
            rate_since_last = packets_since_last / (now - self.last_report_time) if now > self.last_report_time else 0
            
            print(f"Progress: {self.total_packets_sent:,}/{self.TOTAL_PACKETS:,} packets ({self.total_packets_sent/self.TOTAL_PACKETS*100:.2f}%)")
            print(f"Current sending rate: {rate_since_last:.2f} packets/second")
            print(f"Dropped packets: {len(self.dropped_packets):,} ({len(self.dropped_packets)/self.total_packets_sent*100:.2f}%)")
            print(f"Wrap arounds: {self.wrap}")
            print(f"Elapsed time: {elapsed:.2f} seconds")
            print("-" * 50)
            
            self.last_report_time = now
            self.last_report_packets = self.total_packets_sent

    def send_data(self):
        self.start_time = time.time()
        self.last_report_time = self.start_time

        while self.total_packets_sent < self.TOTAL_PACKETS:
            self.window = ""

            for _ in range(self.WINDOW_SIZE):
                if self.total_packets_sent >= self.TOTAL_PACKETS:
                    break 

                seq = ""
                if self.should_drop():
                    seq = f"dropped"
                    self.dropped_packets.append(self.seq_num)
                else: 
                    seq = self.seq_num

                self.window += f"{seq} "

                self.seq_num = (self.seq_num + 1) % self.MAX_SEQ_NUM 
                if self.seq_num == 0:
                    self.wrap += 1

                self.total_packets_sent += 1

            self.socket.sendall(self.window.encode())
            # print(f"{self.window}")

            try :
                data = self.socket.recv(1024).decode().strip().split(" ")
                self.recv_ack = int(data[-1])
                self.total_packets_acked = self.total_packets_sent - len(self.dropped_packets)
            except Exception as e: 
                print(f"Error receiving acks: {e}")
                break

            # Handle retransmissions every 1000 packets
            if self.total_packets_sent % 1000 == 0:
                self.handle_retransmit()
                self.report_statistics()
                print(f"Percent {self.total_packets_sent/self.TOTAL_PACKETS*100:.2f}%")

            # Optional sleep to slow down sending
            time.sleep(0.01)

        print("CHECKEHCKJDKF")
        # Final restransmission to clean up
        # while self.dropped_packets:
        #     self.handle_retransmit()
        #
        #     try: 
        #         data = self.socket.recv(1024).decode().strip().split(" ")
        #         self.total_packets_acked = self.total_packets_sent - len(self.dropped_packets)
        #     except: 
        #         break 
        #
        #     self.record_checkpoint()

        self.report_statistics(force=True)

        print("\nFinal Summary:")
        print("=" * 50)
        print("All sequences sent successfully")
        print(f"Total packets sent: {self.total_packets_sent:,}")
        print(f"Dropped packets remaining: {len(self.dropped_packets):,}")
        success_rate = (self.total_packets_sent - len(self.dropped_packets)) / self.TOTAL_PACKETS * 100
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Total wrap arounds: {self.wrap}")
        elapsed = time.time() - self.start_time
        print(f"Total time: {elapsed:.2f} seconds")
        print(f"Average sending rate: {self.total_packets_sent/elapsed:.2f} packets/second")

        retrans_stats = {1: 0, 2: 0, 3: 0, 4: 0}
        for seq, count in self.retransmission_counts.items():
            if 1 <= count <= 4:
                retrans_stats[count] += 1
            else:
                retrans_stats[4] += 1
        print(f"Retransmission statistics: {retrans_stats}")
        print("-" * 50)
        for i in range(1, 5):
            print(f"Retransmissions of {i}: {retrans_stats[i]}")

        self.save_performance_data()
        self.socket.close()


if __name__ == "__main__":
    client = Client(SERVER_IP, SERVER_PORT)
    if client.connect():
        client.send_data()
