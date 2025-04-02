import socket

def main():
    host = 'localhost'
    port = 5001
    missing_numbers = []  # list to record dropped sequence numbers

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen(1)
        print("Server listening on {}:{}".format(host, port))
        conn, addr = s.accept()
        with conn:
            print("Connected by", addr)
            while True:
                # Read data (we expect the message to contain two lines: start and block)
                data = conn.recv(4096)
                if not data:
                    break
                try:
                    decoded = data.decode()
                    lines = decoded.strip().splitlines()
                    if len(lines) < 2:
                        print("Invalid message format")
                        continue

                    # First line is "start: <starting_sequence_number>"
                    start_line = lines[0]
                    binary_str = lines[1].strip()

                    if not start_line.startswith("start:"):
                        print("Invalid message header")
                        continue

                    start_seq = int(start_line.split(":")[1].strip())
                    if len(binary_str) != 1000:
                        print("Invalid binary string length:", len(binary_str))
                        continue

                    # Calculate cumulative ack:
                    # Walk through the block until the first dropped (0) is found.
                    ack_count = 0
                    for bit in binary_str:
                        if bit == '1':
                            ack_count += 1
                        else:
                            # Record the dropped (missing) sequence number.
                            missing_numbers.append(start_seq + ack_count)
                            break
                    else:
                        # If there were no drops, all 1000 messages are received.
                        ack_count = 1000

                    last_acked = start_seq + len(binary_str)
                    print("Received block starting at {}: Last acked = {}".format(start_seq, last_acked))
                    if missing_numbers:
                        print("Missing numbers length:", len(missing_numbers))

                    # Send back the ack message.
                    ack_message = "ack: {}".format(last_acked)
                    conn.sendall(ack_message.encode())
                except Exception as e:
                    print("Error processing data:", e)

    print("Final missing sequence numbers:", missing_numbers)

if __name__ == '__main__':
    main()
