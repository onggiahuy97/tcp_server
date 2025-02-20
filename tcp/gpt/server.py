#!/usr/bin/env python3
"""
Team Member(s): [Your Name(s)]
CS 258 Project – Server Side
Date: [Submission Date]

Description:
    This server implements a basic TCP sliding-window protocol.
    - Listens on port 12345 and waits for a connection.
    - Performs a handshake: expects "network" from the client and responds with "success".
    - Receives packets formatted as "sequence,window,retransmission_count\n".
    - Uses cumulative ACKs: sends the next expected sequence number as ACK.
    - Tracks:
         * Total packets received (including retransmissions)
         * Unique packets received (in-order arrivals)
         * Missing (dropped) packets (detected via gaps in sequence numbers)
         * Retransmission statistics (counts for 1-4 retransmissions)
         * Goodput over time (logged every 1000 unique packets)
    - After the client disconnects, the server generates four graphs and a CSV file with retransmission stats.
"""

import socket
import time
import matplotlib.pyplot as plt
import csv

def main():
    HOST = ''           # Listen on all available interfaces
    PORT = 12345
    MAX_SEQ = 65536     # 2^16 sequence numbers

    # Create a TCP server socket and bind to the port.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print(f"Server listening on port {PORT}...")

    # Accept a connection from a client.
    conn, addr = server_socket.accept()
    print(f"Connection accepted from {addr}")

    # --- Handshake ---
    try:
        handshake = conn.recv(1024).decode().strip()
        if handshake != "network":
            print("Handshake failed. Expected 'network', got:", handshake)
            conn.close()
            server_socket.close()
            return
        conn.sendall(b"success\n")
    except Exception as e:
        print("Handshake error:", e)
        conn.close()
        server_socket.close()
        return

    # --- Initialize Tracking Variables ---
    expected_seq = 0                   # Next in-order sequence expected
    total_packets_received = 0         # Total packets (including retransmissions)
    unique_packets_received = 0        # Only count first-time (in-order) packets
    missing_packets_count = 0          # Total missing packets detected
    retransmission_stats = {1: 0, 2: 0, 3: 0, 4: 0}

    # Lists for plotting and goodput logging
    start_time = time.time()
    time_list = []       # Timestamps for each processed packet
    window_size_list = []  # Window size (from client) over time
    seq_nums_list = []   # Received sequence numbers
    goodput_times = []   # Timestamps when goodput is logged
    goodput_values = []  # Goodput values (unique/total * 100)
    dropped_records = [] # List of (timestamp, sequence) for missing packets

    buffer = ""  # Buffer to hold incoming data fragments

    # --- Main Reception Loop ---
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                # Client has closed the connection.
                break
            buffer += data.decode()
            # Process complete lines (each packet ends with a newline)
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) != 3:
                    continue  # Ignore malformed packets
                try:
                    seq = int(parts[0])
                    w = int(parts[1])
                    r_count = int(parts[2])
                except ValueError:
                    continue  # Skip packets with non-integer values

                total_packets_received += 1
                now = time.time() - start_time
                time_list.append(now)
                window_size_list.append(w)
                seq_nums_list.append(seq)

                # Determine if the packet is in-order or if there's a gap.
                if seq == expected_seq:
                    unique_packets_received += 1
                    expected_seq = (expected_seq + 1) % MAX_SEQ
                else:
                    # Calculate distance in modulo space.
                    distance = (seq - expected_seq) % MAX_SEQ
                    if 0 < distance < (MAX_SEQ // 2):
                        # A forward jump indicates missing packets.
                        missing_packets_count += distance
                        # Record each missing sequence number.
                        for missing_seq in range(expected_seq, seq):
                            dropped_records.append((now, missing_seq % MAX_SEQ))
                        unique_packets_received += 1
                        expected_seq = (seq + 1) % MAX_SEQ
                    else:
                        # Duplicate or out-of-order packet; ignore for uniqueness.
                        pass

                # Update retransmission statistics for packets with retransmissions.
                if 0 < r_count <= 4:
                    retransmission_stats[r_count] += 1

                # Log goodput every 1000 unique packets.
                if unique_packets_received % 1000 == 0:
                    goodput = (unique_packets_received / total_packets_received) * 100
                    goodput_times.append(now)
                    goodput_values.append(goodput)

                # Send cumulative ACK (next expected sequence number).
                try:
                    conn.sendall(f"{expected_seq}\n".encode())
                except Exception as e:
                    print("Error sending ACK:", e)
                    break

        except Exception as e:
            print("Error receiving data:", e)
            break

    # --- Connection Teardown ---
    conn.close()
    server_socket.close()
    print("Connection closed.")

    # --- Final Statistics ---
    print("Final Statistics:")
    print(f"Total Packets Received (incl. retransmissions): {total_packets_received}")
    print(f"Unique Packets Received: {unique_packets_received}")
    print(f"Missing Packets Detected: {missing_packets_count}")
    final_goodput = (unique_packets_received / total_packets_received * 100) if total_packets_received else 0.0
    print(f"Final Goodput: {final_goodput:.2f}%")
    print("Retransmission counts:")
    for i in range(1, 5):
        print(f"  {i} retries: {retransmission_stats[i]} packets")

    # --- Generate Graphs & CSV Output ---

    # 1) Window Size over Time
    plt.figure()
    plt.plot(time_list, window_size_list, linestyle='-', marker='.', markersize=1)
    plt.xlabel("Time (s)")
    plt.ylabel("Window Size")
    plt.title("Window Size over Time")
    plt.savefig("window_size_over_time.png")

    # 2) Sequence Numbers Received over Time
    plt.figure()
    plt.plot(time_list, seq_nums_list, linestyle='-', marker='.', markersize=1)
    plt.xlabel("Time (s)")
    plt.ylabel("Sequence Number")
    plt.title("Sequence Numbers Received over Time")
    plt.savefig("sequence_numbers_over_time.png")

    # 3) Dropped Sequence Numbers (Scatter Plot)
    plt.figure()
    if dropped_records:
        drop_times, drop_seqs = zip(*dropped_records)
        plt.scatter(drop_times, drop_seqs, s=1)
    plt.xlabel("Time (s)")
    plt.ylabel("Dropped Sequence Number")
    plt.title("Dropped Sequence Numbers over Time")
    plt.savefig("dropped_sequence_numbers.png")

    # 4) Goodput over Time
    plt.figure()
    plt.plot(goodput_times, goodput_values, linestyle='-', marker='o', markersize=3)
    plt.xlabel("Time (s)")
    plt.ylabel("Goodput (%)")
    plt.title("Goodput over Time")
    plt.savefig("goodput_over_time.png")

    # Generate a CSV file with retransmission statistics.
    with open("retransmission_stats.csv", "w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Retransmission Count", "Number of Packets"])
        for count in range(1, 5):
            writer.writerow([count, retransmission_stats[count]])

    # Bar Chart for retransmission statistics.
    plt.figure()
    bars = [retransmission_stats[i] for i in range(1, 5)]
    plt.bar(range(1, 5), bars, tick_label=[str(i) for i in range(1, 5)])
    plt.xlabel("Retransmission Count")
    plt.ylabel("Number of Packets")
    plt.title("Retransmission Statistics")
    plt.savefig("retransmission_stats_bar_chart.png")

    plt.show()

if __name__ == '__main__':
    main()
