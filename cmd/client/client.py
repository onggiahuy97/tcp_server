import socket
import random
import time

SERVER_IP = '127.0.0.1'   # Change if the server is on a different machine
SERVER_PORT = 9000

WINDOW_SIZE = 1000
DROP_PROBABILITY = 0.01    # 1% chance to "drop" a packet
TOTAL_TO_SEND = 10_000_000

def main():
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect((SERVER_IP, SERVER_PORT))
    print("[Client] Connected to server.")

    # 1) Send initial string
    initial_string = "network"
    client_sock.sendall(initial_string.encode())

    # 2) Await "success"
    resp = client_sock.recv(1024).decode().strip()
    print("[Client] Server response:", resp)
    if resp != "success":
        print("[Client] Server didn't respond with 'success'. Exiting.")
        client_sock.close()
        return

    # Sliding window logic
    base = 0        # Oldest unACKed sequence number in total-sent space
    next_seq = 0    # Next new sequence number to send
    in_flight = []  # Track sequence numbers we've sent but not yet ACKed

    # Non-blocking receive so we can keep sending while reading ACKs
    client_sock.settimeout(0.0)

    # Buffer to accumulate partial ACK data
    ack_buffer = ""
    last_ack = -1   # Track the most recent ACK from server

    # Keep going until we've sent everything
    while base < TOTAL_TO_SEND:
        # 1) Send new data while within window
        while next_seq < TOTAL_TO_SEND and (next_seq - base) < WINDOW_SIZE:
            seq_str = f"{next_seq},"
            # "Drop" the packet with a given probability
            if random.random() > DROP_PROBABILITY:
                client_sock.sendall(seq_str.encode())

            in_flight.append(next_seq)
            next_seq += 1

        # 2) Try reading any available ACK data
        try:
            data = client_sock.recv(4096).decode()
            ack_buffer += data
        except:
            # No data ready (non-blocking)
            pass

        # Split ACKs by comma
        acks = ack_buffer.split(',')
        ack_buffer = acks[-1]  # leftover partial piece
        acks = acks[:-1]       # complete ack tokens

        for a in acks:
            a = a.strip()
            if not a:
                continue
            try:
                ack_val = int(a)
            except ValueError:
                continue
            last_ack = ack_val

            # Cumulative ACK means the server has received everything up to ack_val
            # So base should move to ack_val+1 if that is further along
            if ack_val + 1 > base:
                base = ack_val + 1

        # 3) If we see no progress in the ACK (the ack isn't advancing),
        #    we can try a naive retransmit of everything in flight.
        #    This is very simplistic, just to demonstrate the idea.
        if in_flight and base == in_flight[0]:
            # “Retransmit” the in-flight window with the same drop probability
            for seq_num in in_flight:
                seq_str = f"{seq_num},"
                if random.random() > DROP_PROBABILITY:
                    client_sock.sendall(seq_str.encode())
            # A small sleep to avoid saturating
            time.sleep(0.0005)

        # Remove from the front of in_flight anything that’s < base (already ACKed)
        while in_flight and in_flight[0] < base:
            in_flight.pop(0)

    print(f"[Client] Finished sending {TOTAL_TO_SEND} packets (with probabilistic drops).")
    client_sock.close()

if __name__ == "__main__":
    main()
