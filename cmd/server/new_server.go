package main

import (
	"fmt"
	"net"
)

func main() {
	serverAddr := "localhost:8080"
	listener, err := net.Listen("tcp", serverAddr)
	if err != nil {
		fmt.Println("Error starting server:", err)
		return
	}

	defer listener.Close()

	fmt.Printf("Server listening on %s...\n", serverAddr)

	for {
		conn, err := listener.Accept()
		if err != nil {
			fmt.Println("Error accepting connection:", err)
			continue
		}

		go handleConnection(conn)
	}

}

func handleConnection(conn net.Conn) {
	defer conn.Close()

	fmt.Printf("Accepted connection from %s\n", conn.RemoteAddr())

	buffer := make([]byte, 1024)

	for {
		// Read incoming data into the buffer.
		n, err := conn.Read(buffer)
		if err != nil {
			fmt.Println("Error reading:", err)
			return
		}

		data := string(buffer[:n])
		fmt.Printf("Received data: %s", data)

		if data == "network\n" {
			fmt.Printf("Sending: success\n")
			conn.Write([]byte("success\n"))
		} else if data == "finish\n" {
			fmt.Printf("Sending: goodbye\n")
			conn.Write([]byte("goodbye\n"))
			return
		} else {
			fmt.Printf("Sending: unknown\n")
			conn.Write([]byte("unknown\n"))
		}
	}
}
