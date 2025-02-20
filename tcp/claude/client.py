#!/usr/bin/env python3
"""
Dynamic Sliding Window Protocol Client Implementation

This client implements a TCP-like congestion control mechanism using a dynamic sliding window protocol.
The implementation features automatic window size adjustment, packet retransmission, and sequence 
number management.

Key Features:
    - Dynamic Window: Starts at 1 and doubles up to 32 on successful transmission
    - Congestion Control: Window size reduces on packet drops
    - Reliable Delivery: Supports packet retransmission (up to 4 attempts)
    - Sequence Management: Uses modulo 65536 for sequence number wraparound
    - ACK Processing: Handles cumulative acknowledgments from server

Protocol Details:
    - Packet Format: "sequence,window,retransmission_count\n"
    - Drop Simulation: 1% probability of packet loss
    - Retransmission: Every 100 new packets for dropped packets
    - Window Adjustment: Doubles on success, reduces on failure
"""

import socket
import time
import random
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

# Protocol Constants
MAX_SEQUENCE = 65536  # Sequence numbers wrap around at this value
MAX_WINDOW = 32      # Maximum allowed window size
DROP_PROBABILITY = 0.5  # 1% simulated packet loss
RETRANSMIT_INTERVAL = 100  # Retransmit dropped packets every N new packets
MAX_RETRANSMISSIONS = 4    # Maximum retransmission attempts per packet

@dataclass
class ProtocolState:
    """Maintains the current state of the sliding window protocol."""
    dynamic_window: int = 1         # Current window size
    current_seq: int = 0           # Next sequence number to use
    new_packets_sent: int = 0      # Count of new packets attempted
    packets_since_retx: int = 0    # Packets sent since last retransmission
    drop_occurred: bool = False    # Flag for packet drops in current cycle
    
    # Tracking dictionaries
    outstanding: Dict[int, int] = None  # seq -> retransmission_count
    dropped_packets: Dict[int, int] = None  # seq -> retransmission_count
    
    def __post_init__(self):
        """Initialize dictionaries after dataclass creation."""
        self.outstanding = {}
        self.dropped_packets = {}

def seq_before(seq_a: int, seq_b: int, mod: int = MAX_SEQUENCE) -> bool:
    """
    Determines if seq_a comes strictly before seq_b in modulo arithmetic.
    
    Args:
        seq_a: First sequence number
        seq_b: Second sequence number
        mod: Modulus for wraparound (default: MAX_SEQUENCE)
        
    Returns:
        bool: True if seq_a comes before seq_b
    """
    diff = (seq_b - seq_a) % mod
    return 0 < diff < (mod // 2)

class SlidingWindowClient:
    """Implements the sliding window protocol client."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 12345):
        """
        Initialize the client with connection parameters.
        
        Args:
            host: Server hostname or IP address
            port: Server port number
        """
        self.host = host
        self.port = port
        self.socket = None
        self.state = ProtocolState()
    
    def connect(self) -> bool:
        """
        Establish connection with server and perform handshake.
        
        Returns:
            bool: True if connection and handshake successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(0.01)  # Set short timeout for non-blocking ACK reception
            
            # Perform handshake
            self.socket.sendall(b"network\n")
            response = self.socket.recv(1024).decode().strip()
            return response == "success"
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def retransmit_dropped(self) -> None:
        """
        Attempt to retransmit previously dropped packets.
        Packets are retransmitted up to MAX_RETRANSMISSIONS times.
        """
        for seq in list(self.state.dropped_packets.keys()):
            r_count = self.state.dropped_packets[seq]
            if r_count < MAX_RETRANSMISSIONS:
                new_r_count = r_count + 1
                
                # Simulate potential drop for retransmitted packet
                if random.random() < DROP_PROBABILITY:
                    self.state.dropped_packets[seq] = new_r_count
                    self.state.drop_occurred = True
                else:
                    packet = f"{seq},{self.state.dynamic_window},{new_r_count}\n"
                    try:
                        self.socket.sendall(packet.encode())
                        self.state.outstanding[seq] = new_r_count
                        del self.state.dropped_packets[seq]
                    except Exception:
                        pass
            else:
                # Exceeded maximum retransmission attempts
                del self.state.dropped_packets[seq]

    def process_acks(self) -> None:
        """Process acknowledgments from the server."""
        try:
            ack_data = self.socket.recv(4096)
            if ack_data:
                for line in ack_data.decode().splitlines():
                    if line.strip():
                        try:
                            ack_val = int(line.strip())
                            # Remove acknowledged packets
                            to_remove = [seq for seq in self.state.outstanding 
                                       if seq_before(seq, ack_val)]
                            for seq in to_remove:
                                del self.state.outstanding[seq]
                        except ValueError:
                            continue
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error processing ACKs: {e}")

    def adjust_window(self) -> None:
        """
        Adjust the window size based on transmission success/failure.
        Doubles window on success, reduces on failure.
        """
        if not self.state.drop_occurred:
            self.state.dynamic_window = min(self.state.dynamic_window * 2, MAX_WINDOW)
        else:
            self.state.dynamic_window = 16 if self.state.dynamic_window > 16 else self.state.dynamic_window
        self.state.drop_occurred = False

    def transfer_data(self, total_packets: int) -> None:
        """
        Main data transfer loop.
        
        Args:
            total_packets: Number of packets to send
        """
        start_time = time.time()
        
        while (self.state.new_packets_sent < total_packets or 
               self.state.outstanding or self.state.dropped_packets):
               
            # Send new packets if window allows
            while (len(self.state.outstanding) < self.state.dynamic_window and 
                   self.state.new_packets_sent < total_packets):
                   
                seq = self.state.current_seq
                
                # Simulate packet drop
                if random.random() < DROP_PROBABILITY:
                    if seq not in self.state.dropped_packets:
                        self.state.dropped_packets[seq] = 0
                        self.state.drop_occurred = True
                else:
                    packet = f"{seq},{self.state.dynamic_window},0\n"
                    try:
                        self.socket.sendall(packet.encode())
                        self.state.outstanding[seq] = 0
                    except Exception as e:
                        print(f"Error sending packet: {e}")
                        break

                self.state.new_packets_sent += 1
                self.state.packets_since_retx += 1
                self.state.current_seq = (self.state.current_seq + 1) % MAX_SEQUENCE

                # Print progress periodically
                if self.state.new_packets_sent % 10000 == 0:
                    elapsed = time.time() - start_time
                    print(f"Progress: {self.state.new_packets_sent}/{total_packets} "
                          f"packets sent, Elapsed: {elapsed:.1f}s")

                # Handle retransmission and window adjustment
                if self.state.packets_since_retx >= RETRANSMIT_INTERVAL:
                    self.retransmit_dropped()
                    self.state.packets_since_retx = 0
                    self.adjust_window()

            # Process incoming ACKs
            self.process_acks()

            # Handle final retransmissions
            if self.state.new_packets_sent >= total_packets and self.state.dropped_packets:
                self.retransmit_dropped()

        elapsed = time.time() - start_time
        print(f"Transfer complete. Total packets: {self.state.new_packets_sent} "
              f"in {elapsed:.2f}s")

    def close(self) -> None:
        """Close the client connection."""
        if self.socket:
            self.socket.close()

def main():
    """Main entry point for the client."""
    client = SlidingWindowClient()
    
    if client.connect():
        print("Connected to server successfully.")
        try:
            client.transfer_data(total_packets=10_000_000)
        except KeyboardInterrupt:
            print("\nTransfer interrupted by user.")
        finally:
            client.close()
    else:
        print("Failed to connect to server.")

if __name__ == '__main__':
    main()