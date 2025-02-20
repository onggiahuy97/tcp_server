#!/usr/bin/env python3
"""
Team Member(s): [Your Name(s)]
CS 258 Project – Client Side (Dynamic Sliding Window)
Date: [Submission Date]

Description:
    This client implements a dynamic sliding window protocol that mimics TCP congestion control.
    - The window starts at 1 and doubles (up to a maximum of 32) if no drops occur.
    - If a packet drop (simulated with a 1% probability) is detected, the window is reduced.
    - Packets are formatted as "sequence,window,retransmission_count\n", and sequence numbers
      wrap around modulo 65536.
    - Dropped packets are retransmitted every 100 new packets (up to 4 attempts per packet).
    - ACKs from the server (cumulative, indicating the next expected sequence number) are used to
      remove acknowledged packets.
    - Only essential progress information is printed.
"""

import socket
import time
import random

MAX_SEQ = 65536  # Sequence numbers range from 0 to 65535

def seq_before(seq_a, seq_b, mod=MAX_SEQ):
    """
    Returns True if seq_a comes strictly before seq_b in modulo arithmetic.
    """
    diff = (seq_b - seq_a) % mod
    return 0 < diff < (mod // 2)

def main():
    HOST = '127.0.0.1'         # Server IP (adjust if needed)
    PORT = 12345
    total_packets = 10_000_000  # For debugging; change to 10_000_000 for final submission
    drop_probability = 0.01    # 1% chance to simulate a packet drop
    max_window = 32            # Maximum window size allowed

    # Dynamic sliding window variables:
    dynamic_window = 1         # Initial window size
    drop_occurred = False      # Flag to indicate if any drop occurred during the current cycle

    # Create and connect the socket.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))

    # --- Handshake ---
    s.sendall(b"network\n")
    response = s.recv(1024).decode().strip()
    if response != "success":
        print("Handshake failed.")
        s.close()
        return
    print("Handshake successful.")

    # Set a short timeout for non-blocking ACK reception.
    s.settimeout(0.01)

    current_seq = 0         # Current sequence number (wraps at MAX_SEQ)
    new_packets_sent = 0    # Count of new (non-retransmitted) packets attempted
    outstanding = {}        # Dictionary: {sequence: retransmission_count} for in-flight packets
    dropped_packets = {}    # Dictionary: {sequence: retransmission_count} for packets not sent due to drop
    retransmit_interval = 100   # Retransmit dropped packets every 100 new packets
    packets_since_retx = 0
    start_time = time.time()

    def retransmit_dropped():
        """
        Attempt to retransmit packets that were dropped, up to 4 attempts each.
        """
        nonlocal dynamic_window, drop_occurred
        for seq in list(dropped_packets.keys()):
            r_count = dropped_packets[seq]
            if r_count < 4:
                new_r_count = r_count + 1
                # Simulate drop for retransmitted packet as well.
                if random.random() < drop_probability:
                    dropped_packets[seq] = new_r_count
                    drop_occurred = True
                else:
                    packet = f"{seq},{dynamic_window},{new_r_count}\n"
                    try:
                        s.sendall(packet.encode())
                        outstanding[seq] = new_r_count
                        del dropped_packets[seq]
                    except Exception:
                        pass
            else:
                # Exceeded maximum retransmission attempts; drop packet.
                del dropped_packets[seq]

    # --- Main Transmission Loop ---
    while new_packets_sent < total_packets or outstanding or dropped_packets:
        # Send new packets if the number of outstanding packets is below the dynamic window.
        while len(outstanding) < dynamic_window and new_packets_sent < total_packets:
            seq = current_seq
            # Simulate a packet drop.
            if random.random() < drop_probability:
                if seq not in dropped_packets:
                    dropped_packets[seq] = 0
                    drop_occurred = True
            else:
                packet = f"{seq},{dynamic_window},0\n"
                try:
                    s.sendall(packet.encode())
                    outstanding[seq] = 0
                except Exception:
                    pass

            new_packets_sent += 1
            packets_since_retx += 1
            current_seq = (current_seq + 1) % MAX_SEQ

            # Print progress every 10,000 new packets.
            if new_packets_sent % 10000 == 0:
                elapsed = time.time() - start_time
                print(f"Progress: {new_packets_sent}/{total_packets} packets sent, Elapsed: {elapsed:.1f}s")

            # Every retransmit_interval new packets, attempt to retransmit dropped packets.
            if packets_since_retx >= retransmit_interval:
                retransmit_dropped()
                packets_since_retx = 0
                # Adjust window size: if no drop occurred, double the window; if a drop occurred, reduce it.
                if not drop_occurred:
                    dynamic_window = min(dynamic_window * 2, max_window)
                else:
                    dynamic_window = 16 if dynamic_window > 16 else dynamic_window
                drop_occurred = False

        # Poll for ACKs from the server.
        try:
            ack_data = s.recv(4096)
            if ack_data:
                for line in ack_data.decode().splitlines():
                    if line.strip():
                        try:
                            ack_val = int(line.strip())
                            # Remove outstanding packets that are acknowledged (i.e., come before ack_val).
                            to_remove = [seq for seq in outstanding if seq_before(seq, ack_val)]
                            for seq in to_remove:
                                del outstanding[seq]
                        except ValueError:
                            continue
        except socket.timeout:
            pass
        except Exception:
            break

        # If all new packets have been sent, continue retransmitting dropped packets.
        if new_packets_sent >= total_packets and dropped_packets:
            retransmit_dropped()

    s.close()
    elapsed = time.time() - start_time
    print(f"Transfer complete. Total new packets attempted: {new_packets_sent} in {elapsed:.2f}s.")

if __name__ == '__main__':
    main()
