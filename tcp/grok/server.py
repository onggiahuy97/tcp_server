#!/usr/bin/env python3
"""
TCP-like Sliding Window Protocol Server (Enhanced)

This server implements a TCP-like sliding window protocol with robust packet
processing, detailed performance tracking, and comprehensive visualizations.

Key Features:
    - Cumulative ACKs: Sends the next expected sequence number.
    - Performance Tracking: Monitors total/unique packets, missing packets, and goodput.
    - Visualization: Generates 5 graphs with empty data handling and timestamps.
    - Statistics: Logs retransmissions to CSV and console.
    - Robustness: Includes timeouts, better buffer management, and error logging.

Packet Format:
    "sequence,window,retransmission_count\n"

Sequence Space:
    0 to 65535 (wraps around at 65536)

Performance Logging:
    - Goodput logged every 1000 total packets.
    - Progress logged every 100k packets.

Output:
    - 5 timestamped graphs (e.g., window_size_20250220_123456.png).
    - retransmission_stats.csv with retransmission counts.

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
from datetime import datetime

# ------------------------------- Constants --------------------------------- #
MAX_SEQUENCE = 65536               # 2^16 sequence numbers
DEFAULT_PORT = 12345               # Default server port
BUFFER_SIZE = 4096                 # Socket receive buffer size
GOODPUT_LOGGING_INTERVAL = 1000    # Log goodput every N total packets
PROGRESS_LOG_INTERVAL = 100000     # Log progress every N packets
TIMEOUT = 10.0                     # Socket timeout in seconds

# ---------------------------- Data Structures ------------------------------ #
@dataclass
class NetworkStatistics:
    """
    Tracks network performance statistics for the sliding window protocol.

    Attributes:
        total_packets (int): Total packets received (including duplicates).
        unique_packets (int): Unique packets received.
        missing_packets (int): Count of missing packets detected.
        expected_seq (int): Next expected sequence number.
        start_time (float): Timestamp when receiving started.
        retransmission_counts (dict): Maps retransmission count to packet count.
        times (list): Timestamps for each packet.
        window_sizes (list): Window sizes reported by client.
        sequence_numbers (list): Sequence numbers received.
        dropped_packets (list): (time, seq) for detected missing packets.
        goodput_records (list): (time, goodput) for goodput over time.
    """
    total_packets: int = 0
    unique_packets: int = 0
    missing_packets: int = 0
    expected_seq: int = 0
    start_time: float = field(default_factory=time.time)
    retransmission_counts: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    times: List[float] = field(default_factory=list)
    window_sizes: List[int] = field(default_factory=list)
    sequence_numbers: List[int] = field(default_factory=list)
    dropped_packets: List[Tuple[float, int]] = field(default_factory=list)
    goodput_records: List[Tuple[float, float]] = field(default_factory=list)

    def log_progress(self) -> None:
        """Log progress to console if total_packets meets interval."""
        if self.total_packets > 0 and self.total_packets % PROGRESS_LOG_INTERVAL == 0:
            elapsed = time.time() - self.start_time
            print(f"Progress: {self.total_packets:,} total, {self.unique_packets:,} unique, "
                  f"goodput: {self.calculate_goodput():.1f}%, time: {elapsed:.1f}s")

    def record_packet(self, seq: int, window: int, retransmit_count: int) -> None:
        """
        Record packet statistics.

        Args:
            seq (int): Sequence number.
            window (int): Client-reported window size.
            retransmit_count (int): Number of retransmissions.
        """
        self.total_packets += 1
        current_time = time.time() - self.start_time
        self.times.append(current_time)
        self.window_sizes.append(window)
        self.sequence_numbers.append(seq)
        if 0 < retransmit_count <= 4:
            self.retransmission_counts[retransmit_count] += 1

    def update_sequence_tracking(self, seq: int) -> None:
        """
        Update expected sequence and detect missing packets.

        Args:
            seq (int): Received sequence number.
        """
        if seq == self.expected_seq:
            self.unique_packets += 1
            self.expected_seq = (self.expected_seq + 1) % MAX_SEQUENCE
        else:
            distance = (seq - self.expected_seq) % MAX_SEQUENCE
            if 0 < distance < (MAX_SEQUENCE // 2):  # Forward gap, not wrap-around
                self.missing_packets += distance
                current_time = time.time() - self.start_time
                for missing_seq in range(self.expected_seq, seq):
                    self.dropped_packets.append((current_time, missing_seq % MAX_SEQUENCE))
                self.unique_packets += 1
                self.expected_seq = (seq + 1) % MAX_SEQUENCE

    def calculate_goodput(self) -> float:
        """Calculate goodput as percentage of unique/total packets."""
        return (self.unique_packets / self.total_packets * 100.0) if self.total_packets > 0 else 0.0

    def record_goodput(self) -> None:
        """Record goodput if total_packets meets interval."""
        if self.total_packets > 0 and self.total_packets % GOODPUT_LOGGING_INTERVAL == 0:
            current_time = time.time() - self.start_time
            goodput = self.calculate_goodput()
            self.goodput_records.append((current_time, goodput))

# ---------------------- Visualization & Persistence ------------------------ #
class NetworkVisualizer:
    """Handles generation of plots and CSV output with enhanced robustness."""
    @staticmethod
    def _get_timestamp() -> str:
        """Generate a timestamp for filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def _plot_or_placeholder(x_data: List, y_data: List, xlabel: str, ylabel: str, title: str, filename: str, scatter: bool = False) -> None:
        """Helper to plot data or show a placeholder if empty."""
        timestamp = NetworkVisualizer._get_timestamp()
        plt.figure()
        if x_data and y_data:
            if scatter:
                plt.scatter(x_data, y_data, s=1)
            else:
                plt.plot(x_data, y_data, linestyle='-', marker='.', markersize=1)
        else:
            plt.text(0.5, 0.5, "No data available", ha='center', va='center')
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        plt.savefig(f"{filename}_{timestamp}.png")
        plt.close()

    @classmethod
    def generate_visualizations(cls, stats: NetworkStatistics) -> None:
        """
        Generate and save all visualizations with timestamps.

        Args:
            stats (NetworkStatistics): Collected metrics.
        """
        # 1. Window Size over Time
        cls._plot_or_placeholder(stats.times, stats.window_sizes, "Time (s)", "Window Size",
                                 "Window Size over Time", "window_size_over_time")

        # 2. Sequence Numbers over Time
        cls._plot_or_placeholder(stats.times, stats.sequence_numbers, "Time (s)", "Sequence Number",
                                 "Sequence Numbers over Time", "sequence_numbers_over_time")

        # 3. Dropped Packets over Time
        drop_times, drop_seqs = zip(*stats.dropped_packets) if stats.dropped_packets else ([], [])
        cls._plot_or_placeholder(drop_times, drop_seqs, "Time (s)", "Dropped Sequence Number",
                                 "Dropped Sequence Numbers", "dropped_sequence_numbers", scatter=True)

        # 4. Goodput over Time
        goodput_times, goodput_values = zip(*stats.goodput_records) if stats.goodput_records else ([], [])
        cls._plot_or_placeholder(goodput_times, goodput_values, "Time (s)", "Goodput (%)",
                                 "Goodput over Time", "goodput_over_time")

        # 5. Retransmission Statistics (Bar Chart)
        timestamp = cls._get_timestamp()
        plt.figure()
        counts = [stats.retransmission_counts[i] for i in range(1, 5)]
        if any(counts):
            plt.bar(range(1, 5), counts, tick_label=[str(i) for i in range(1, 5)])
        else:
            plt.text(0.5, 0.5, "No retransmissions recorded", ha='center', va='center')
        plt.xlabel("Retransmission Count")
        plt.ylabel("Number of Packets")
        plt.title("Retransmission Statistics")
        plt.savefig(f"retransmission_stats_bar_chart_{timestamp}.png")
        plt.close()

    @staticmethod
    def save_retransmission_stats(stats: NetworkStatistics) -> None:
        """
        Save retransmission data to CSV.

        Args:
            stats (NetworkStatistics): Collected retransmission data.
        """
        timestamp = NetworkVisualizer._get_timestamp()
        with open(f"retransmission_stats_{timestamp}.csv", "w", newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Retransmission Count", "Number of Packets"])
            for count in range(1, 5):
                writer.writerow([count, stats.retransmission_counts[count]])

# ------------------------------ Server Class ------------------------------- #
class SlidingWindowServer:
    """
    Server-side implementation of the sliding window protocol with enhanced robustness.
    """
    def __init__(self, host: str = '', port: int = DEFAULT_PORT):
        """
        Initialize server with connection parameters.

        Args:
            host (str): Host address (default: all interfaces).
            port (int): Port number.
        """
        self.host = host
        self.port = port
        self.socket = None
        self.connection = None
        self.stats = NetworkStatistics()
        self.buffer = ""

    def start(self) -> None:
        """Start the server socket and listen for connections."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(TIMEOUT)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        print(f"Server listening on port {self.port}...")

    def accept_connection(self) -> bool:
        """
        Accept a client connection with handshake.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self.connection, addr = self.socket.accept()
            self.connection.settimeout(TIMEOUT)
            print(f"Connection accepted from {addr}")
            handshake = self.connection.recv(BUFFER_SIZE).decode().strip()
            if handshake != "network":
                print(f"Handshake failed. Expected 'network', got: {handshake}")
                return False
            self.connection.sendall(b"success\n")
            return True
        except socket.timeout:
            print("Handshake timed out.")
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def run(self) -> None:
        """Main loop to receive and process packets."""
        while True:
            try:
                data = self.connection.recv(BUFFER_SIZE)
                if not data:
                    print("Client disconnected.")
                    break
                self.buffer += data.decode()
                while "\n" in self.buffer:
                    packet, self.buffer = self.buffer.split("\n", 1)
                    packet = packet.strip()
                    if packet:
                        self.process_packet(packet)
            except socket.timeout:
                print("Receive timeout; continuing to listen...")
                continue
            except Exception as e:
                print(f"Error in main loop: {e}")
                break

    def process_packet(self, packet: str) -> bool:
        """
        Process a single packet and send ACK.

        Args:
            packet (str): Packet data.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            seq_str, win_str, rtx_str = packet.split(',')
            seq, window, retransmit_count = int(seq_str), int(win_str), int(rtx_str)
            self.stats.record_packet(seq, window, retransmit_count)
            self.stats.update_sequence_tracking(seq)
            self.stats.record_goodput()
            self.stats.log_progress()
            ack_msg = f"{self.stats.expected_seq}\n"
            self.connection.sendall(ack_msg.encode())
            return True
        except ValueError:
            print(f"Malformed packet: {packet}")
            return False
        except Exception as e:
            print(f"Error processing packet {packet}: {e}")
            return False

    def print_statistics(self) -> None:
        """Print final statistics."""
        print("\nFinal Statistics:")
        print(f"  Total Packets: {self.stats.total_packets:,}")
        print(f"  Unique Packets: {self.stats.unique_packets:,}")
        print(f"  Missing Packets: {self.stats.missing_packets:,}")
        print(f"  Final Goodput: {self.stats.calculate_goodput():.2f}%")
        print("Retransmission Counts:")
        for i in range(1, 5):
            print(f"    {i} retries: {self.stats.retransmission_counts[i]:,} packets")

    def cleanup(self) -> None:
        """Close connections and generate outputs."""
        if self.connection:
            self.connection.close()
        if self.socket:
            self.socket.close()
        print("\nGenerating visualizations and stats...")
        NetworkVisualizer.generate_visualizations(self.stats)
        NetworkVisualizer.save_retransmission_stats(self.stats)
        print("Server shutdown complete.")

# ------------------------- Main Entry Point -------------------------------- #
def main():
    """Main entry point for the server."""
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

if __name__ == "__main__":
    main()
