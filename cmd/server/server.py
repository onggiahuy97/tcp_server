import socket

HOST = "127.0.0.1"  # Localhost
PORT = 12345        # Port to listen on

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        print(f"Server listening on {HOST}:{PORT}...")

        conn, addr = server_socket.accept()
        with conn:
            print(f"Connected by {addr}")

            # Receive the initial message
            data = conn.recv(1024).decode().strip()
            if data == "network":
                print("Received 'network' message, sending 'success' response.")
                conn.sendall(b"success")

                # Communication loop
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break  # Connection closed by client
                    print(f"Client: {data.decode().strip()}")
                    response = input("Server: ")  # Reply manually
                    conn.sendall(response.encode())

            else:
                print("Unexpected message received, closing connection.")
                conn.close()

if __name__ == "__main__":
    start_server()
