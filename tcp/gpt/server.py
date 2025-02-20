#!/usr/bin/env python3
"""
TCP-like Sliding Window Protocol Server (Easier to Understand)

This server implements a TCP-like sliding window protocol that tracks and analyzes
network performance metrics. It processes incoming packets, manages sequence numbers,
and generates performance visualizations.

Key Features:
    - Cumulative ACKs: Acknowledges packets by sending the "next expected" sequence number.
    - Performance Tracking: Monitors packet stats (total, unique, missing) and goodput.
    - Visualization: Generates graphs for window size, sequence numbers, drops, and goodput.
    - Statistics: Logs retransmission counts and network performance metrics to a CSV file.
    
Packet Format:
    "sequence,window,retransmission_count\n"
    
Sequence Space:
    0 to 65535 (wraps around at 65536)
    
Performance Logging:
    - Goodput is calculated every 1000 unique packets.
    - Progress is logged to stdout every 100k packets.
    
Output:
    - 5 graph images (e.g., window_size_over_time.png).
    - A retransmission_stats.csv file with detailed statistics.

Usage:
    python3 server_script.py
"""

import socket
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
import csv
from collections import defaultdict

# ------------------------------- Constants --------------------------------- #
MAX_SEQUENCE = 65536               # 2^16 sequence numbers
DEFAULT_PORT = 12345               # Default server port
BUFFER_SIZE = 4096                 # Socket receive buffer size
GOODPUT_LOGGING_INTERVAL = 1000    # Log goodput every N unique packets

# ---------------------------- Data Structures ------------------------------ #
@dataclass
class NetworkStatistics:
    """
    Tracks network performance statistics for the sliding window protocol.
    
    Attributes:
        total_packets (int): Total packets received (including duplicates).
        unique_packets (int): Unique (new) packets received.
        missing_packets (int): Count of missing packets detected (out-of-sequence).
        expected_seq (int): The next sequence number we expect to receive.
        start_time (float): Timestamp when we started receiving packets.
        
        retransmission_counts (dict[int, int]): Maps retransmission count -> number of packets.
        
        times (list[float]): Records the time (since start) when each packet was processed.
        window_sizes (list[int]): Window size values corresponding to each packet time.
        sequence_numbers (list[int]): Sequence numbers received over time.
        
        dropped_packets (list[tuple[float, int]]): (time, seq) for each detected missing packet.
        goodput_records (list[tuple[float, float]]): (time, goodput_percent) for logging goodput over time.
    """
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

    def should_log_progress(self) -> bool:
        """
        Check if we should log progress to the console based on packet count.

        Returns:
            bool: True if total_packets is a multiple of 100k.
        """
        return (self.total_packets > 0 and 
                self.total_packets % 100000 == 0)

    def get_progress_stats(self) -> str:
        """
        Construct a string summarizing current progress (goodput, etc.).

        Returns:
            str: Formatted progress information.
        """
        elapsed = time.time() - self.start_time
        return (f"Progress: {self.total_packets:,} total packets, "
                f"{self.unique_packets:,} unique, "
                f"goodput: {self.calculate_goodput():.1f}%, "
                f"time: {elapsed:.1f}s")

    def record_packet(self, seq: int, window: int, retransmit_count: int) -> None:
        """
        Record statistics for each received packet.
        
        Args:
            seq (int): Sequence number of the received packet.
            window (int): The window size reported by the client.
            retransmit_count (int): How many times this packet has been retransmitted.
        """
        self.total_packets += 1

        # Record time-based data for plotting
        current_time = time.time() - self.start_time
        self.times.append(current_time)
        self.window_sizes.append(window)
        self.sequence_numbers.append(seq)

        # Track retransmission counts (1..4).
        if 0 < retransmit_count <= 4:
            self.retransmission_counts[retransmit_count] += 1

    def update_sequence_tracking(self, seq: int) -> None:
        """
        Update our expected sequence number and detect missing packets.
        
        Args:
            seq (int): The sequence number of the current packet.
        """
        # If the packet is exactly the one we're expecting, increment expected_seq
        if seq == self.expected_seq:
            self.unique_packets += 1
            self.expected_seq = (self.expected_seq + 1) % MAX_SEQUENCE
        else:
            # Calculate distance in a wrap-around sense
            distance = (seq - self.expected_seq) % MAX_SEQUENCE
            # If this packet is ahead (but not too far to indicate wrap-around)
            if 0 < distance < (MAX_SEQUENCE // 2):
                # Mark the missing range
                self.missing_packets += distance

                # Record each missing sequence as dropped
                current_time = time.time() - self.start_time
                for missing_seq in range(self.expected_seq, seq):
                    self.dropped_packets.append((current_time, missing_seq % MAX_SEQUENCE))

                # Update expected_seq to the next one after the newly received seq
                self.unique_packets += 1
                self.expected_seq = (seq + 1) % MAX_SEQUENCE

    def calculate_goodput(self) -> float:
        """
        Calculate the current goodput as a percentage (unique / total).

        Returns:
            float: Goodput percentage.
        """
        if self.total_packets == 0:
            return 0.0
        return (self.unique_packets / self.total_packets) * 100.0

    def record_goodput(self) -> None:
        """
        Log goodput periodically for plotting.
        """
        if self.unique_packets % GOODPUT_LOGGING_INTERVAL == 0:
            current_time = time.time() - self.start_time
            goodput = self.calculate_goodput()
            self.goodput_records.append((current_time, goodput))

# ---------------------- Visualization & Persistence ------------------------ #
class NetworkVisualizer:
    """
    Handles the generation of various plots (window size, sequence numbers, 
    dropped packets, goodput, retransmission stats) and saving them as image files,
    as well as saving retransmission stats to a CSV.
    """

    @staticmethod
    def generate_visualizations(stats: NetworkStatistics) -> None:
        """
        Generate and save all visualizations.

        Args:
            stats (NetworkStatistics): Collected metrics from the server run.
        """
        # 1. Window Size over Time
        plt.figure()
        plt.plot(stats.times, stats.window_sizes, linestyle='-', marker='.', markersize=1)
        plt.xlabel("Time (s)")
        plt.ylabel("Window Size")
        plt.title("Window Size over Time")
        plt.savefig("window_size_over_time.png")
        plt.close()

        # 2. Sequence Numbers over Time
        plt.figure()
        plt.plot(stats.times, stats.sequence_numbers, linestyle='-', marker='.', markersize=1)
        plt.xlabel("Time (s)")
        plt.ylabel("Sequence Number")
        plt.title("Sequence Numbers over Time")
        plt.savefig("sequence_numbers_over_time.png")
        plt.close()

        # 3. Dropped Packets over Time
        plt.figure()
        if stats.dropped_packets:
            drop_times, drop_seqs = zip(*stats.dropped_packets)
            plt.scatter(drop_times, drop_seqs, s=1)
        plt.xlabel("Time (s)")
        plt.ylabel("Dropped Sequence Number")
        plt.title("Dropped Sequence Numbers")
        plt.savefig("dropped_sequence_numbers.png")
        plt.close()

        # 4. Goodput over Time
        plt.figure()
        if stats.goodput_records:
            times, values = zip(*stats.goodput_records)
            plt.plot(times, values, linestyle='-', marker='o', markersize=3)
        plt.xlabel("Time (s)")
        plt.ylabel("Goodput (%)")
        plt.title("Goodput over Time")
        plt.savefig("goodput_over_time.png")
        plt.close()

        # 5. Retransmission Statistics (Bar Chart)
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
        Save retransmission data to a CSV file.

        Args:
            stats (NetworkStatistics): Collected retransmission data.
        """
        with open("retransmission_stats.csv", "w", newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Retransmission Count", "Number of Packets"])
            for count in range(1, 5):
                writer.writerow([count, stats.retransmission_counts[count]])

# ------------------------------ Server Class ------------------------------- #
class SlidingWindowServer:
    """
    Implements the server-side of the sliding window protocol, including:
      - Accepting a single client connection.
      - Performing a simple handshake.
      - Receiving packets and extracting (sequence, window, retransmit_count).
      - Maintaining and logging statistics (goodput, missing packets, etc.).
      - Sending cumulative ACKs to the client.
      - Generating final plots and CSV data upon completion.
    """

    def __init__(self, host: str = '', port: int = DEFAULT_PORT):
        """
        Initialize the server with connection parameters.
        
        Args:
            host (str): Host address to bind to (default: all interfaces).
            port (int): Port number to listen on.
        """
        self.host = host
        self.port = port
        self.socket = None
        self.connection = None
        self.stats = NetworkStatistics()
        self.buffer = ""

    # ------------------------- Setup and Handshake -------------------------- #
    def start(self) -> None:
        """
        Start the server socket and listen for incoming connections.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        print(f"Server listening on port {self.port}...")

    def accept_connection(self) -> bool:
        """
        Accept a client connection and perform the initial handshake.
        
        Returns:
            bool: True if handshake is successful, False otherwise.
        """
        try:
            self.connection, addr = self.socket.accept()
            print(f"Connection accepted from {addr}")

            # Receive handshake string
            handshake = self.connection.recv(1024).decode().strip()
            if handshake != "network":
                print(f"Handshake failed. Expected 'network', got: {handshake}")
                return False

            # Respond with success
            self.connection.sendall(b"success\n")
            return True

        except Exception as e:
            print(f"Connection error during handshake: {e}")
            return False

    # -------------------------- Main Processing ----------------------------- #
    def run(self) -> None:
        """
        Main loop to receive and process packets from the client, until the
        client disconnects or an error occurs.
        """
        while True:
            try:
                data = self.connection.recv(BUFFER_SIZE)
                if not data:
                    # Client closed the connection.
                    break

                # Append decoded data to our buffer
                self.buffer += data.decode()

                # Process complete lines (packets) from the buffer
                while "\n" in self.buffer:
                    packet, self.buffer = self.buffer.split("\n", 1)
                    packet = packet.strip()
                    if packet:
                        self.process_packet(packet)

            except Exception as e:
                print(f"Error in main receiving loop: {e}")
                break

    def process_packet(self, packet: str) -> bool:
        """
        Parse and process a single packet, updating statistics and sending ACKs.
        
        Args:
            packet (str): Packet in the format "sequence,window,retransmission_count"
            
        Returns:
            bool: True if processed successfully, False otherwise.
        """
        try:
            seq_str, win_str, rtx_str = packet.split(',')
            seq, window, retransmit_count = int(seq_str), int(win_str), int(rtx_str)

            # 1. Record the packet stats
            self.stats.record_packet(seq, window, retransmit_count)

            # 2. Update sequence tracking for missing packets
            self.stats.update_sequence_tracking(seq)

            # 3. Periodically record goodput
            self.stats.record_goodput()

            # 4. Log progress every 100k packets
            if self.stats.should_log_progress():
                print(self.stats.get_progress_stats())

            # 5. Send cumulative ACK (the next expected sequence)
            ack_msg = f"{self.stats.expected_seq}\n"
            self.connection.sendall(ack_msg.encode())

            return True

        except ValueError:
            # Malformed packet
            return False
        except Exception as e:
            print(f"Error processing packet: {e}")
            return False

    # ------------------------- Finalization Steps --------------------------- #
    def print_statistics(self) -> None:
        """
        Print final statistics to the console (called upon shutdown).
        """
        print("\nFinal Statistics:")
        print(f"  Total Packets Received: {self.stats.total_packets}")
        print(f"  Unique Packets Received: {self.stats.unique_packets}")
        print(f"  Missing Packets Detected: {self.stats.missing_packets}")
        print(f"  Final Goodput: {self.stats.calculate_goodput():.2f}%\n")

        print("Retransmission counts:")
        for i in range(1, 5):
            print(f"  {i} retries: {self.stats.retransmission_counts[i]} packets")

    def cleanup(self) -> None:
        """
        Cleanup resources: close connections and generate output (plots, CSV).
        """
        if self.connection:
            self.connection.close()
        if self.socket:
            self.socket.close()

        print("\nGenerating visualizations...")
        NetworkVisualizer.generate_visualizations(self.stats)
        NetworkVisualizer.save_retransmission_stats(self.stats)
        print("Server shutdown complete.")

# ------------------------- Main Entry Point -------------------------------- #
def main():
    """
    Main entry point for the server script. It sets up the server, accepts a single
    client connection, then processes incoming packets until the client disconnects.
    """
    server = SlidingWindowServer(host="", port=DEFAULT_PORT)

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
