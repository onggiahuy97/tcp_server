import socket
import random
import time

def generate_block(start_seq, length=1000, drop_prob=0.01):
    """
    Generate a binary string of length `length` where each bit is:
      '1' for a non-dropped packet,
      '0' for a dropped packet (with probability drop_prob).
    """
    return ''.join('0' if random.random() < drop_prob else '1' for _ in range(length))

def main():
    host = 'localhost'
    port = 5001
    start_seq = 1  # initial sequence number

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        while start_seq < 1_000_000:
            # Create a block with the current starting sequence number.
            block = generate_block(start_seq, 1000, drop_prob=0.01)
            # Format the message with two lines: first the start number, then the 1000-bit block.
            message = "start: {}\n{}".format(start_seq, block)
            s.sendall(message.encode())
            print("Sent block starting at", start_seq)

            # Wait for the server's acknowledgement.
            data = s.recv(1024)
            if not data:
                print("Server closed connection")
                break

            ack_message = data.decode().strip()
            if not ack_message.startswith("ack:"):
                print("Invalid ack from server:", ack_message)
                break

            # Parse the ack and update the starting sequence number.
            ack_seq = int(ack_message.split(":")[1].strip())
            print("Server acked up to:", ack_seq)

            # If no progress was made (due to a drop at the very beginning), wait and retry.
            if ack_seq == start_seq:
                print("No progress, resending block...")
                time.sleep(0.1)
            else:
                start_seq = ack_seq

            # Optionally pause between blocks.
            time.sleep(0.01)

if __name__ == '__main__':
    main()
