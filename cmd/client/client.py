import socket

HOST = "127.0.0.1"  # Server's hostname or IP address
PORT = 12345        # Port to connect to

def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))
        print("Connected to server.")

        # Send the initialization message
        client_socket.sendall(b"network")

        # Wait for the response
        response = client_socket.recv(1024).decode().strip()
        if response == "success":
            print("Connection established successfully!")

            # Communication loop
            while True:
                message = input("Client: ")  # Send message
                if not message:
                    break  # Exit if input is empty
                client_socket.sendall(message.encode())

                data = client_socket.recv(1024)
                if not data:
                    break  # Server closed connection
                print(f"Server: {data.decode().strip()}")

        else:
            print("Unexpected response from server, closing connection.")

if __name__ == "__main__":
    start_client()
