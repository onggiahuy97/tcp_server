#!/usr/bin/env python3
"""
Static Sliding Window Protocol Client

This client implements a TCP-like sliding window data transfer using a fixed
window size. It features:
    1. A fixed window size.
    2. Packet drop simulation (1% probability).
    3. Reliable delivery with packet retransmissions (up to 4 attempts).
    4. Sequence number wraparound (modulo 65536).
    5. Cumulative ACK handling.

Key Points:
    - Packet Format: "sequence,window,retransmission_count\n"
    - Drop Simulation: 1% probability of packet loss
    - Retransmission Trigger: Every 100 new packets
    - Sequence Numbers: Wrap around at 65536
    - ACK Processing: Removes all outstanding packets with sequence < ack

Recommended Usage:
    python3 this_script.py

Note: This code is for demonstration purposes. It simulates packet loss and shows
      how a sliding window protocol might behave in an unreliable environment.
"""

import socket
import time
import random
from typing import Dict
from dataclasses import dataclass, field

# ------------------------------- Constants ---------------------------------- #
MAX_SEQUENCE = 65536      # Sequence numbers wrap around at this value
STATIC_WINDOW = 4        # Fixed window size
DROP_PROBABILITY = 0.01   # 1% simulated packet loss
RETRANSMIT_INTERVAL = 100 # Retransmit dropped packets every N new packets
MAX_RETRANSMISSIONS = 4   # Maximum retransmission attempts per packet
TOTAL_PACKETS = 10_000_000   # Total packets to send in the demo

# ---------------------------- Helper Functions ------------------------------ #
def is_sequence_before(seq_a: int, seq_b: int, mod: int = MAX_SEQUENCE) -> bool:
    """
    Check if seq_a is strictly before seq_b in modulo arithmetic.

    Args:
        seq_a (int): First sequence number.
        seq_b (int): Second sequence number.
        mod (int): The wraparound threshold for sequence numbers.

    Returns:
        bool: True if seq_a is before seq_b in the wrapping sense.
    """
    diff = (seq_b - seq_a) % mod
    return 0 < diff < (mod // 2)

# ----------------------------- Data Classes --------------------------------- #
@dataclass
class ProtocolState:
    """
    ProtocolState holds variables needed for the sliding window logic.
    
    Attributes:
        window_size (int): Fixed window size.
        next_sequence (int): Next sequence number to send, wraps at MAX_SEQUENCE.
        total_sent (int): Count of new (not retransmitted) packets sent so far.
        since_last_retransmit (int): Count of new packets since the last retransmission cycle.
        outstanding (Dict[int, int]): Mapping of sequence -> retransmission_count for packets sent but not yet ACKed.
        dropped (Dict[int, int]): Mapping of sequence -> retransmission_count for packets known to be dropped.
    """
    window_size: int = STATIC_WINDOW
    next_sequence: int = 0
    total_sent: int = 0
    since_last_retransmit: int = 0
    outstanding: Dict[int, int] = field(default_factory=dict)
    dropped: Dict[int, int] = field(default_factory=dict)

# ---------------------------- Client Class ---------------------------------- #
class SlidingWindowClient:
    """
    SlidingWindowClient manages a TCP-like sliding window data transfer to a server.
    
    Main responsibilities:
      1. Connect to the server and perform an initial handshake.
      2. Send data in a loop, respecting the fixed window size.
      3. Simulate packet drops and handle retransmissions.
      4. Process cumulative acknowledgments to update the window.
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 12345, window_size: int = STATIC_WINDOW):
        """
        Constructor initializes the server address and the internal state.
        
        Args:
            host (str): Server hostname or IP address.
            port (int): Server port number.
            window_size (int): Fixed window size for the protocol.
        """
        self.host = host
        self.port = port
        self.socket = None
        self.state = ProtocolState(window_size=window_size)

    def connect(self) -> bool:
        """
        Establishes a connection with the server and performs a simple handshake.
        
        Returns:
            bool: True if the connection and handshake succeed, False otherwise.
        """
        try:
            # Create a TCP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(0.5)  # Non-blocking read for incoming ACKs

            # Send handshake to the server
            self.socket.sendall(b"network\n")
            response = self.socket.recv(1024).decode().strip()

            # Expecting "success" as a handshake response
            return response == "success"

        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def close(self) -> None:
        """
        Closes the connection to the server (if open).
        """
        if self.socket:
            self.socket.close()
            self.socket = None

    # --------------------------- Main Operations ---------------------------- #
    def start_data_transfer(self, total_packets: int) -> None:
        """
        Main loop for sending packets until all new packets are sent and all
        outstanding or dropped packets are resolved.

        Args:
            total_packets (int): The total number of new packets to send.
        """
        start_time = time.time()

        while self._incomplete_transfer(total_packets):
            # 1. Send new packets while there is room in the window and packets remain.
            while (len(self.state.outstanding) < self.state.window_size and
                   self.state.total_sent < total_packets):
                self._send_new_packet()

            # 2. Process ACKs from the server (may free up space in the window).
            self._process_acks()

            # 3. Retransmit dropped packets at regular intervals.
            if self.state.since_last_retransmit >= RETRANSMIT_INTERVAL:
                self._retransmit_dropped()
                self.state.since_last_retransmit = 0

            # 4. If all new packets have been sent but there are still dropped packets,
            #    retransmit them to ensure reliable delivery.
            if self.state.total_sent >= total_packets and self.state.dropped:
                self._retransmit_dropped()

        elapsed = time.time() - start_time
        print(f"Transfer complete. Total packets sent: {self.state.total_sent} "
              f"in {elapsed:.2f} seconds.")

    def _incomplete_transfer(self, total_packets: int) -> bool:
        """
        Determines if the data transfer is still in progress.

        Args:
            total_packets (int): The total packets intended to be sent.

        Returns:
            bool: True if transfer is still ongoing, False otherwise.
        """
        still_have_new_to_send = self.state.total_sent < total_packets
        unacknowledged_packets = bool(self.state.outstanding) or bool(self.state.dropped)
        return still_have_new_to_send or unacknowledged_packets

    # -------------------------- Packet Operations --------------------------- #
    def _send_new_packet(self) -> None:
        """
        Sends a new packet (or marks it as dropped if simulated). Updates state accordingly.
        """
        seq = self.state.next_sequence

        # Simulate packet drop for new packet
        if random.random() < DROP_PROBABILITY:
            # Mark as dropped with 0 retransmissions so far
            self.state.dropped[seq] = 0
        else:
            # Attempt to send the packet
            packet_str = f"{seq},{self.state.window_size},0\n"
            try:
                self.socket.sendall(packet_str.encode())
                # Add to outstanding with retransmission_count=0
                self.state.outstanding[seq] = 0
            except Exception as e:
                print(f"Error sending packet seq={seq}: {e}")
                return

        # Update counters
        self.state.total_sent += 1
        self.state.since_last_retransmit += 1
        self.state.next_sequence = (seq + 1) % MAX_SEQUENCE

        # Log progress periodically
        if self.state.total_sent % 10000 == 0:
            print(f"Progress: {self.state.total_sent} packets sent.")

    def _retransmit_dropped(self) -> None:
        """
        Attempts to retransmit previously dropped packets (up to MAX_RETRANSMISSIONS).
        """
        for seq, r_count in list(self.state.dropped.items()):
            if r_count < MAX_RETRANSMISSIONS:
                new_r_count = r_count + 1

                # Simulate potential drop for retransmitted packet
                if random.random() < DROP_PROBABILITY:
                    self.state.dropped[seq] = new_r_count
                else:
                    packet_str = f"{seq},{self.state.window_size},{new_r_count}\n"
                    try:
                        self.socket.sendall(packet_str.encode())
                        # Move packet to outstanding
                        self.state.outstanding[seq] = new_r_count
                        del self.state.dropped[seq]
                    except Exception as e:
                        print(f"Retransmit error seq={seq}: {e}")
            else:
                # Exceeded maximum retransmissions; remove it
                del self.state.dropped[seq]

    # --------------------------- ACK Processing ----------------------------- #
    def _process_acks(self) -> None:
        """
        Processes incoming ACKs and removes acknowledged packets from the outstanding list.
        """
        try:
            ack_data = self.socket.recv(4096)
            if not ack_data:
                return

            for line in ack_data.decode().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    ack_value = int(line)
                except ValueError:
                    continue

                # Remove all outstanding packets with sequence < ack_value in the modulo sense
                to_remove = [seq for seq in self.state.outstanding
                             if is_sequence_before(seq, ack_value)]
                for seq in to_remove:
                    del self.state.outstanding[seq]

        except socket.timeout:
            # No ACKs received; this is expected sometimes.
            pass
        except Exception as e:
            print(f"Error processing ACKs: {e}")

# ------------------------- Script Entry Point ------------------------------- #
def main():
    """Main entry point for the client script."""
    client = SlidingWindowClient(host="127.0.0.1", port=12345, window_size=STATIC_WINDOW)

    if client.connect():
        print("Connected to server successfully. Starting data transfer...")
        try:
            # Adjust the total_packets as needed for your demonstration.
            client.start_data_transfer(total_packets=TOTAL_PACKETS)
        except KeyboardInterrupt:
            print("\nTransfer interrupted by user.")
        finally:
            client.close()
    else:
        print("Failed to connect to server.")

if __name__ == '__main__':
    main()
