import socket

HOST = '0.0.0.0'   # Listen on all interfaces
PORT = 9000        # Adjust if needed

def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((HOST, PORT))
    server_sock.listen()
    print(f"[Server] Listening on {HOST}:{PORT}")

    conn, addr = server_sock.accept()
    print(f"[Server] Client connected: {addr}")

    # 1) Receive the initial connection string
    init_data = conn.recv(1024).decode().strip()
    print(f"[Server] Received initial string: {init_data}")

    # 2) Send "success" back
    conn.sendall(b"success")

    # Server-side tracking
    next_expected = 0                 # Next in-order sequence we expect
    out_of_order = set()             # Temporarily store out-of-order packets
    unique_received = set()          # Track all distinct seq nums we've seen
    total_received = 0               # Count of distinct packets
    total_sent_estimate = 0          # We'll estimate how many were sent to compute goodput
    
    # For periodic goodput computation
    goodput_sum = 0.0
    goodput_count = 0
    GOODPUT_INTERVAL = 1000          # Recompute goodput after every 1000 new packets

    TARGET = 10_000_000              # Stop after receiving 10 million unique

    # Buffer used for partial reads
    buffer = b''

    while total_received < TARGET:
        chunk = conn.recv(4096)
        if not chunk:
            # Connection might have closed or lost
            break

        buffer += chunk
        # We’ll split by comma (sequence numbers come comma-separated)
        parts = buffer.split(b',')
        # The last piece in `parts` may be incomplete, so keep it in `buffer`
        buffer = parts[-1]
        parts = parts[:-1]

        for p in parts:
            p = p.strip()
            if not p:
                continue

            try:
                seq_num = int(p)
            except ValueError:
                # Invalid chunk; skip
                continue

            # Only count this seq_num if it's truly new
            if seq_num not in unique_received:
                unique_received.add(seq_num)
                total_received += 1

                # If it's exactly the next expected, we can advance
                if seq_num == next_expected:
                    next_expected += 1
                    # Check if we can advance further (any out_of_order ones that now fill the gap)
                    while next_expected in out_of_order:
                        out_of_order.remove(next_expected)
                        next_expected += 1
                elif seq_num > next_expected:
                    # We have a gap
                    out_of_order.add(seq_num)
                # If seq_num < next_expected, it’s a duplicate or older, ignore

                # Periodically compute a rough goodput
                if (total_received % GOODPUT_INTERVAL) == 0:
                    # Our “sent” estimate is the largest seq_num seen + 1
                    # (This is an oversimplification, ignoring wrap-around.)
                    largest_seen = max(unique_received) if unique_received else 0
                    total_sent_estimate = largest_seen + 1

                    gp = 1.0
                    if total_sent_estimate > 0:
                        gp = total_received / total_sent_estimate

                    goodput_sum += gp
                    goodput_count += 1
                    avg_goodput = goodput_sum / goodput_count

                    print(f"[Server] Received={total_received}, "
                          f"EstimatedSent={total_sent_estimate}, "
                          f"InstantGoodput={gp:.4f}, "
                          f"AvgGoodput={avg_goodput:.4f}")

            # Send a cumulative ACK = (next_expected - 1)
            # Because everything below next_expected is considered in-order received
            ack_val = next_expected - 1
            ack_msg = str(ack_val) + ","
            conn.sendall(ack_msg.encode())

            if total_received >= TARGET:
                break

        if total_received >= TARGET:
            break

    print(f"[Server] Done receiving. Total distinct packets = {total_received}")
    conn.close()
    server_sock.close()

if __name__ == "__main__":
    main()
