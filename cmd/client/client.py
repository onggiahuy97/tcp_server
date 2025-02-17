import socket

def connect_to_server():
    # Create a TCP socket
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Connect to the server
        server_address = ('localhost', 8080)
        print(f"Connecting to server at {server_address[0]}:{server_address[1]}")
        client.connect(server_address)
        
        # Send the message
        message = "network\n"
        print(f"Sending message: {message.strip()}")
        client.send(message.encode())
        
        # Receive the response
        response = client.recv(1024).decode()
        print(f"Server response: {response.strip()}")

        # Send finish message 
        message = "finish\n"
        print(f"Sending message: {message.strip()}")
        client.send(message.encode())

        # Receive the response
        response = client.recv(1024).decode()
        print(f"Server response: {response.strip()}")

        if response.strip() == "goodbyte":
            print("Closing connection")
            client.close()
            return 
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        print("Closing connection")
        client.close()

if __name__ == "__main__":
    connect_to_server()
