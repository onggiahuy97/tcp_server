#!/usr/bin/env python3
"""
TCP-like Sliding Window Protocol Server Implementation

This server implements a TCP-like sliding window protocol that tracks and analyzes
network performance metrics. It processes incoming packets, manages sequence numbers,
and generates comprehensive performance visualizations.

Key Features:
    - Cumulative ACK System: Acknowledges packets by sending next expected sequence number
    - Performance Tracking: Monitors packet statistics and network performance
    - Visualization: Generates graphs for window size, sequence numbers, drops, and goodput
    - Statistics: Records detailed retransmission statistics and network performance metrics

Protocol Details:
    - Packet Format: "sequence,window,retransmission_count\n"
    - Sequence Space: 0 to 65535 (wraps around)
    - Performance Logging: Goodput calculated every 1000 unique packets
    - Output: Generates 5 graphs and a CSV file with transmission statistics
"""

import socket
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
import csv
from collections import defaultdict

# Protocol Constants
MAX_SEQUENCE = 65536  # 2^16 sequence numbers
DEFAULT_PORT = 12345
BUFFER_SIZE = 4096
GOODPUT_LOGGING_INTERVAL = 1000  # Log goodput every N unique packets

@dataclass
class NetworkStatistics:
    """Tracks network performance statistics."""
    total_packets: int = 0
    unique_packets: int = 0
    missing_packets: int = 0
    expected_seq: int = 0
    start_time: float = field(default_factory=time.time)
    retransmission_counts: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    # Time series data for plotting
    times: List[float] = field(default_factory=list)
    window_sizes: List[int] = field(default_factory=list)
    sequence_numbers: List[int] = field(default_factory=list)
    dropped_packets: List[Tuple[float, int]] = field(default_factory=list)
    goodput_records: List[Tuple[float, float]] = field(default_factory=list)

    def should_log(self) -> bool:
        """Check if we should log progress based on packet count."""
        return (self.total_packets > 0 and 
                self.total_packets % 100000 == 0)  # Log every 100k packets

    def get_progress_stats(self) -> str:
        """Get a concise progress status string."""
        elapsed = time.time() - self.start_time
        return (f"Progress: {self.total_packets:,} total packets, "
                f"{self.unique_packets:,} unique, "
                f"goodput: {self.calculate_goodput():.1f}%, "
                f"time: {elapsed:.1f}s")

    def record_packet(self, seq: int, window: int, retransmit_count: int) -> None:
        """
        Record statistics for a received packet.
        
        Args:
            seq: Sequence number of the packet
            window: Current window size from client
            retransmit_count: Number of retransmissions for this packet
        """
        current_time = time.time() - self.start_time
        self.total_packets += 1
        self.times.append(current_time)
        self.window_sizes.append(window)
        self.sequence_numbers.append(seq)

        if 0 < retransmit_count <= 4:
            self.retransmission_counts[retransmit_count] += 1

    def update_sequence_tracking(self, seq: int) -> None:
        """
        Update sequence number tracking and missing packet detection.
        
        Args:
            seq: Current sequence number
        Returns:
            int: Next expected sequence number
        """
        if seq == self.expected_seq:
            self.unique_packets += 1
            self.expected_seq = (self.expected_seq + 1) % MAX_SEQUENCE
        else:
            distance = (seq - self.expected_seq) % MAX_SEQUENCE
            if 0 < distance < (MAX_SEQUENCE // 2):
                self.missing_packets += distance
                current_time = time.time() - self.start_time
                
                # Record each missing sequence number
                for missing_seq in range(self.expected_seq, seq):
                    self.dropped_packets.append((current_time, missing_seq % MAX_SEQUENCE))
                
                self.unique_packets += 1
                self.expected_seq = (seq + 1) % MAX_SEQUENCE

    def calculate_goodput(self) -> float:
        """Calculate current goodput percentage."""
        return (self.unique_packets / self.total_packets * 100) if self.total_packets else 0.0

    def record_goodput(self) -> None:
        """Record current goodput for plotting."""
        if self.unique_packets % GOODPUT_LOGGING_INTERVAL == 0:
            current_time = time.time() - self.start_time
            goodput = self.calculate_goodput()
            self.goodput_records.append((current_time, goodput))

class NetworkVisualizer:
    """Handles visualization of network statistics."""
    
    @staticmethod
    def generate_visualizations(stats: NetworkStatistics) -> None:
        """
        Generate all visualization plots and save them to files.
        
        Args:
            stats: NetworkStatistics object containing all recorded data
        """
        # Window Size Plot
        plt.figure()
        plt.plot(stats.times, stats.window_sizes, linestyle='-', marker='.', markersize=1)
        plt.xlabel("Time (s)")
        plt.ylabel("Window Size")
        plt.title("Window Size over Time")
        plt.savefig("window_size_over_time.png")
        plt.close()

        # Sequence Numbers Plot
        plt.figure()
        plt.plot(stats.times, stats.sequence_numbers, linestyle='-', marker='.', markersize=1)
        plt.xlabel("Time (s)")
        plt.ylabel("Sequence Number")
        plt.title("Sequence Numbers Received over Time")
        plt.savefig("sequence_numbers_over_time.png")
        plt.close()

        # Dropped Packets Plot
        plt.figure()
        if stats.dropped_packets:
            drop_times, drop_seqs = zip(*stats.dropped_packets)
            plt.scatter(drop_times, drop_seqs, s=1)
        plt.xlabel("Time (s)")
        plt.ylabel("Dropped Sequence Number")
        plt.title("Dropped Sequence Numbers over Time")
        plt.savefig("dropped_sequence_numbers.png")
        plt.close()

        # Goodput Plot
        plt.figure()
        if stats.goodput_records:
            times, values = zip(*stats.goodput_records)
            plt.plot(times, values, linestyle='-', marker='o', markersize=3)
        plt.xlabel("Time (s)")
        plt.ylabel("Goodput (%)")
        plt.title("Goodput over Time")
        plt.savefig("goodput_over_time.png")
        plt.close()

        # Retransmission Statistics Plot
        plt.figure()
        counts = [stats.retransmission_counts[i] for i in range(1, 5)]
        plt.bar(range(1, 5), counts, tick_label=[str(i) for i in range(1, 5)])
        plt.xlabel("Retransmission Count")
        plt.ylabel("Number of Packets")
        plt.title("Retransmission Statistics")
        plt.savefig("retransmission_stats_bar_chart.png")
        plt.close()

    @staticmethod
    def save_retransmission_stats(stats: NetworkStatistics) -> None:
        """
        Save retransmission statistics to CSV file.
        
        Args:
            stats: NetworkStatistics object containing retransmission data
        """
        with open("retransmission_stats.csv", "w", newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Retransmission Count", "Number of Packets"])
            for count in range(1, 5):
                writer.writerow([count, stats.retransmission_counts[count]])

class SlidingWindowServer:
    """Implements the sliding window protocol server."""
    
    def __init__(self, host: str = '', port: int = DEFAULT_PORT):
        """
        Initialize the server with connection parameters.
        
        Args:
            host: Host address to bind to (default: all interfaces)
            port: Port number to listen on
        """
        self.host = host
        self.port = port
        self.socket = None
        self.connection = None
        self.stats = NetworkStatistics()
        self.buffer = ""

    def start(self) -> None:
        """Start the server and listen for connections."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        print(f"Server listening on port {self.port}...")

    def accept_connection(self) -> bool:
        """
        Accept a client connection and perform handshake.
        
        Returns:
            bool: True if connection and handshake successful
        """
        try:
            self.connection, addr = self.socket.accept()
            print(f"Connection accepted from {addr}")
            
            # Perform handshake
            handshake = self.connection.recv(1024).decode().strip()
            if handshake != "network":
                print(f"Handshake failed. Expected 'network', got: {handshake}")
                return False
                
            self.connection.sendall(b"success\n")
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def process_packet(self, packet: str) -> bool:
        """
        Process a single packet and update statistics.
        
        Args:
            packet: Packet string in format "sequence,window,retransmission_count"
            
        Returns:
            bool: True if packet processed successfully
        """
        try:
            seq, window, retransmit_count = map(int, packet.split(','))
            
            self.stats.record_packet(seq, window, retransmit_count)
            self.stats.update_sequence_tracking(seq)
            self.stats.record_goodput()

            if self.stats.should_log():
                print(self.stats.get_progress_stats())
            
            # Send cumulative ACK
            self.connection.sendall(f"{self.stats.expected_seq}\n".encode())
            return True
        except ValueError:
            return False  # Malformed packet
        except Exception as e:
            print(f"Error processing packet: {e}")
            return False

    def run(self) -> None:
        """Main server loop for receiving and processing packets."""
        while True:
            try:
                data = self.connection.recv(BUFFER_SIZE)
                if not data:
                    break
                    
                self.buffer += data.decode()
                while "\n" in self.buffer:
                    packet, self.buffer = self.buffer.split("\n", 1)
                    if packet.strip():
                        self.process_packet(packet.strip())
            except Exception as e:
                print(f"Error in main loop: {e}")
                break

    def print_statistics(self) -> None:
        """Print final statistics to console."""
        print("\nFinal Statistics:")
        print(f"Total Packets Received: {self.stats.total_packets}")
        print(f"Unique Packets Received: {self.stats.unique_packets}")
        print(f"Missing Packets Detected: {self.stats.missing_packets}")
        print(f"Final Goodput: {self.stats.calculate_goodput():.2f}%")
        print("\nRetransmission counts:")
        for i in range(1, 5):
            print(f"  {i} retries: {self.stats.retransmission_counts[i]} packets")

    def cleanup(self) -> None:
        """Clean up connections and generate final output."""
        if self.connection:
            self.connection.close()
        if self.socket:
            self.socket.close()
        
        print("\nGenerating visualizations...")
        NetworkVisualizer.generate_visualizations(self.stats)
        NetworkVisualizer.save_retransmission_stats(self.stats)
        print("Server shutdown complete.")

def main():
    """Main entry point for the server."""
    server = SlidingWindowServer()
    
    try:
        server.start()
        if server.accept_connection():
            server.run()
    except KeyboardInterrupt:
        print("\nServer interrupted by user.")
    finally:
        server.print_statistics()
        server.cleanup()

if __name__ == '__main__':
    main()